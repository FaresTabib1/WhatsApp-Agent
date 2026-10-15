"""
Routes Business.

AVERTISSEMENT : Ces endpoints ne sont pas encore sécurisés.
Aucun mécanisme d'authentification n'existe à ce stade.
L'autorisation sera ajoutée lorsque l'authentification sera implémentée.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessRead

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    db: AsyncSession = Depends(get_db),
) -> Business:
    business = Business(name=payload.name)
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Business:
    business = await db.get(Business, business_id)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    return business
