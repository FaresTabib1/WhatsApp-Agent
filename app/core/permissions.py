import uuid
from functools import lru_cache
from typing import Callable
from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.business import Business
from app.models.business_member import BusinessMember, MemberRole
from app.models.user import User

async def _get_membership(
    business_id: uuid.UUID,
    user: User,
    session: AsyncSession,
) -> BusinessMember:

    business = await session.get(Business, business_id)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )

    result = await session.execute(
        select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return member

@lru_cache
def require_business_member(
    required_role: MemberRole | None = None,
) -> Callable:

    async def dependency(
        business_id: uuid.UUID = Path(...),
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> BusinessMember:
        member = await _get_membership(business_id, user, session)

        if required_role == MemberRole.owner:
            if member.role != MemberRole.owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Owner role required",
                )
        return member

    return dependency
