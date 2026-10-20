"""
Tests API pour GET /integrations/instagram/connect et callback.
SQLite en mémoire. httpx vers Meta entièrement mocké.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Réponses Meta mockées
_SHORT_TOKEN_RESPONSE = {"access_token": "short_token_abc", "token_type": "bearer"}
_LONG_TOKEN_RESPONSE = {"access_token": "long_token_xyz", "expires_in": 5183944}
_ME_BUSINESS_RESPONSE = {
    "id": "17841400000000001",
    "username": "boutique_test",
    "account_type": "BUSINESS",
}
_ME_PERSONAL_RESPONSE = {
    "id": "17841400000000002",
    "username": "personal_user",
    "account_type": "PERSONAL",
}


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_ID", "test_app_id")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test_app_secret")
    monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "http://localhost:8000/integrations/instagram/callback")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# --- Helpers ---

async def _register_and_token(client, email="owner@test.com"):
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    return r.json()["access_token"]


async def _create_business(client, token, name="Boutique"):
    r = await client.post(
        "/businesses",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()


def _mock_meta_responses(account_type_response=None):
    """Context manager mockant les 3 appels httpx vers Meta."""
    if account_type_response is None:
        account_type_response = _ME_BUSINESS_RESPONSE

    responses = [
        MagicMock(json=lambda: _SHORT_TOKEN_RESPONSE, raise_for_status=lambda: None),
        MagicMock(json=lambda: _LONG_TOKEN_RESPONSE, raise_for_status=lambda: None),
        MagicMock(json=lambda: account_type_response, raise_for_status=lambda: None),
    ]
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=responses[0])
    mock_client.get = AsyncMock(side_effect=responses[1:])
    return mock_client


# --- GET /integrations/instagram/connect ---

@pytest.mark.asyncio
async def test_connect_returns_authorize_url(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "authorize_url" in data
    assert "instagram.com/oauth/authorize" in data["authorize_url"]


@pytest.mark.asyncio
async def test_connect_url_contains_state(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert "state=" in r.json()["authorize_url"]


@pytest.mark.asyncio
async def test_connect_url_contains_scope(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert "instagram_business_basic" in r.json()["authorize_url"]


@pytest.mark.asyncio
async def test_connect_unauthenticated_returns_403(client):
    r = await client.get(
        f"/integrations/instagram/connect?business_id={uuid.uuid4()}",
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_connect_non_member_returns_403(client):
    owner = await _register_and_token(client, "owner@test.com")
    other = await _register_and_token(client, "other@test.com")
    biz = await _create_business(client, owner)
    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_connect_member_not_owner_returns_403(client, db_session):
    """Un member (pas owner) ne peut pas connecter Instagram."""
    owner = await _register_and_token(client, "owner@test.com")
    member_token = await _register_and_token(client, "member@test.com")
    biz = await _create_business(client, owner)

    # Créer un BusinessMember explicitement
    from app.models.business_member import BusinessMember, MemberRole
    from sqlalchemy import select
    from app.models.user import User

    result = await db_session.execute(
        select(User).where(User.email == "member@test.com")
    )
    member_user = result.scalar_one()
    membership = BusinessMember(
        business_id=uuid.UUID(biz["id"]),
        user_id=member_user.id,
        role=MemberRole.member,
    )
    db_session.add(membership)
    await db_session.commit()

    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_connect_business_not_found_returns_404(client):
    token = await _register_and_token(client)
    r = await client.get(
        f"/integrations/instagram/connect?business_id={uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# --- GET /integrations/instagram/callback ---

@pytest.mark.asyncio
async def test_callback_invalid_state_returns_400(client):
    r = await client.get(
        "/integrations/instagram/callback?code=abc&state=invalid_state",
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_callback_expired_state_returns_400(client):
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.security import SECRET_KEY, ALGORITHM

    expired_payload = {
        "purpose": "instagram_oauth",
        "business_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_state = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    r = await client.get(
        f"/integrations/instagram/callback?code=abc&state={expired_state}",
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_callback_access_token_as_state_returns_400(client):
    """Un access token ne peut pas être réutilisé comme state CSRF."""
    from app.core.security import create_access_token
    fake_state = create_access_token("some-user-id")
    r = await client.get(
        f"/integrations/instagram/callback?code=abc&state={fake_state}",
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_callback_success_creates_connection(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    # Obtenir un vrai state
    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    url = r.json()["authorize_url"]
    state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]

    mock_client = _mock_meta_responses()
    with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
        r = await client.get(
            f"/integrations/instagram/callback?code=test_code&state={state}",
        )

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "active"
    assert data["provider"] == "instagram"
    assert data["provider_account_id"] == "17841400000000001"
    assert data["username"] == "boutique_test"
    assert "access_token" not in str(data)
    assert "token_encrypted" not in str(data)


@pytest.mark.asyncio
async def test_callback_token_not_in_response(client):
    """Le token ne doit jamais apparaître dans la réponse."""
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    url = r.json()["authorize_url"]
    state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]

    mock_client = _mock_meta_responses()
    with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
        r = await client.get(
            f"/integrations/instagram/callback?code=test_code&state={state}",
        )

    response_str = str(r.json())
    assert "long_token_xyz" not in response_str
    assert "short_token_abc" not in response_str


@pytest.mark.asyncio
async def test_callback_personal_account_returns_422(client):
    """Un compte Instagram personnel (PERSONAL) est rejeté."""
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    url = r.json()["authorize_url"]
    state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]

    mock_client = _mock_meta_responses(account_type_response=_ME_PERSONAL_RESPONSE)
    with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
        r = await client.get(
            f"/integrations/instagram/callback?code=test_code&state={state}",
        )

    assert r.status_code == 422
    assert "Business or Creator" in r.json()["detail"]


@pytest.mark.asyncio
async def test_callback_meta_error_returns_502(client):
    """Une erreur Meta (ex: code invalide) retourne 502."""
    import httpx as httpx_lib
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    url = r.json()["authorize_url"]
    state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("Meta unreachable"))

    with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
        r = await client.get(
            f"/integrations/instagram/callback?code=bad_code&state={state}",
        )

    assert r.status_code == 502


@pytest.mark.asyncio
async def test_callback_reconnect_updates_existing_connection(client):
    """Reconnecter le même compte met à jour la connexion existante sans doublon."""
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    async def _do_connect():
        r = await client.get(
            f"/integrations/instagram/connect?business_id={biz['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        url = r.json()["authorize_url"]
        state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]
        mock_client = _mock_meta_responses()
        with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
            return await client.get(
                f"/integrations/instagram/callback?code=test_code&state={state}",
            )

    r1 = await _do_connect()
    r2 = await _do_connect()

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


# --- GET /integrations/instagram/status/{business_id} ---

@pytest.mark.asyncio
async def test_status_no_connection_returns_null(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/integrations/instagram/status/{biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.asyncio
async def test_status_after_connect_returns_active(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)

    r = await client.get(
        f"/integrations/instagram/connect?business_id={biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    url = r.json()["authorize_url"]
    state = [p.split("=", 1)[1] for p in url.split("?")[1].split("&") if p.startswith("state=")][0]

    mock_client = _mock_meta_responses()
    with patch("app.integrations.meta_instagram.oauth.httpx.AsyncClient", return_value=mock_client):
        await client.get(
            f"/integrations/instagram/callback?code=test_code&state={state}",
        )

    r = await client.get(
        f"/integrations/instagram/status/{biz['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert "access_token" not in str(r.json())


@pytest.mark.asyncio
async def test_status_cross_tenant_returns_404(client):
    """Un user ne peut pas voir le statut d'une boutique à laquelle il n'appartient pas."""
    owner_a = await _register_and_token(client, "a@test.com")
    owner_b = await _register_and_token(client, "b@test.com")
    biz_a = await _create_business(client, owner_a)

    r = await client.get(
        f"/integrations/instagram/status/{biz_a['id']}",
        headers={"Authorization": f"Bearer {owner_b}"},
    )
    assert r.status_code == 403
