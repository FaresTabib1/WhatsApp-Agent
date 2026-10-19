import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_business_member
from app.models.business import Business
from app.models.business_member import BusinessMember, MemberRole
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessRead

router = APIRouter(prefix="/businesses", tags=["businesses"])

@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Business:
    business = Business(name=payload.name)
    db.add(business)
    await db.flush()  
    member = BusinessMember(
        business_id=business.id,
        user_id=current_user.id,
        role=MemberRole.owner,
    )
    db.add(member)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> Business:
    business = await db.get(Business, business_id)
    return business