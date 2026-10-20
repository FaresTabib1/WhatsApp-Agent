import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.encryption import encrypt_token
from app.core.permissions import _get_membership, require_business_member
from app.core.security import create_oauth_state, decode_oauth_state
from app.integrations.meta_instagram.oauth import build_authorize_url, exchange_code_for_token
from app.models.business_member import BusinessMember, MemberRole
from app.models.connection import Connection, ConnectionProvider, ConnectionStatus
from app.models.user import User
from app.schemas.instagram import ConnectResponse, ConnectionStatusRead, SyncResponse
from app.services.instagram_import_service import InstagramImportService

router = APIRouter(prefix="/integrations/instagram", tags=["instagram"])


@router.get("/connect", response_model=ConnectResponse)
async def instagram_connect(
    business_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectResponse:
    # Vérifier owner uniquement
    member = await _get_membership(business_id, current_user, session)
    if member.role != MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the business owner can connect an Instagram account",
        )

    state = create_oauth_state(
        business_id=str(business_id),
        user_id=str(current_user.id),
    )
    authorize_url = build_authorize_url(state=state)
    return ConnectResponse(authorize_url=authorize_url)


@router.get("/callback", response_model=ConnectionStatusRead)
async def instagram_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> ConnectionStatusRead:
    state_data = decode_oauth_state(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please restart the connection flow.",
        )

    business_id = uuid.UUID(state_data.business_id)

    try:
        token_data = await exchange_code_for_token(code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Meta. Please try again.",
        )

    encrypted_token = encrypt_token(token_data["access_token"])
    ig_user_id = token_data["ig_user_id"]

    # Rechercher une connexion existante pour cet ig_user_id
    result = await session.execute(
        select(Connection).where(
            Connection.provider == ConnectionProvider.instagram,
            Connection.provider_account_id == ig_user_id,
            Connection.business_id == business_id,
        )
    )
    connection = result.scalar_one_or_none()

    meta = {
        "ig_user_id": ig_user_id,
        "username": token_data["username"],
        "account_type": token_data["account_type"],
        "token_expires_at": token_data["token_expires_at"],
        "token_encrypted": encrypted_token,
    }

    if connection is None:
        connection = Connection(
            business_id=business_id,
            provider=ConnectionProvider.instagram,
            provider_account_id=ig_user_id,
            status=ConnectionStatus.active,
            secret_ref=None,
            meta=meta,
        )
        session.add(connection)
    else:
        connection.status = ConnectionStatus.active
        connection.meta = meta

    await session.commit()
    await session.refresh(connection)

    return ConnectionStatusRead(
        id=connection.id,
        business_id=connection.business_id,
        provider=connection.provider.value,
        provider_account_id=connection.provider_account_id,
        status=connection.status.value,
        username=token_data["username"],
        account_type=token_data["account_type"],
        token_expires_at=token_data["token_expires_at"],
    )


@router.post(
    "/sync/{business_id}/{connection_id}",
    response_model=SyncResponse,
)
async def sync_instagram_posts(
    business_id: uuid.UUID,
    connection_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member()),
    session: AsyncSession = Depends(get_db),
) -> SyncResponse:
    service = InstagramImportService(session=session)
    result = await service.sync_connection(
        connection_id=connection_id,
        business_id=business_id,
    )

    if result.error and result.total_fetched == 0:
        status_code = 400
        if result.token_expired:
            status_code = 401
        raise HTTPException(status_code=status_code, detail=result.error)

    return SyncResponse(
        connection_id=result.connection_id,
        total_fetched=result.total_fetched,
        created=result.created,
        skipped=result.skipped,
        failed=result.failed,
        token_expired=result.token_expired,
        rate_limited=result.rate_limited,
        error=result.error,
    )


@router.get(
    "/status/{business_id}",
    response_model=ConnectionStatusRead | None,
)
async def instagram_connection_status(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionStatusRead | None:
    await _get_membership(business_id, current_user, session)

    result = await session.execute(
        select(Connection).where(
            Connection.business_id == business_id,
            Connection.provider == ConnectionProvider.instagram,
        )
    )
    connection = result.scalar_one_or_none()

    if connection is None:
        return None

    meta = connection.meta or {}
    return ConnectionStatusRead(
        id=connection.id,
        business_id=connection.business_id,
        provider=connection.provider.value,
        provider_account_id=connection.provider_account_id,
        status=connection.status.value,
        username=meta.get("username"),
        account_type=meta.get("account_type"),
        token_expires_at=meta.get("token_expires_at"),
    )