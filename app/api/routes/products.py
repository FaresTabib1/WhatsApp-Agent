import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.permissions import require_business_member
from app.models.business import Business
from app.models.business_member import BusinessMember, MemberRole
from app.models.product import Product, ProductSourceType, ProductStatus, ProductVariant
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, ProductVariantRead

router = APIRouter(
    prefix="/businesses/{business_id}/products",
    tags=["products"],
)

@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    business_id: uuid.UUID,
    payload: ProductCreate,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    business = await db.get(Business, business_id)

    currency = payload.currency
    if currency is None and business.default_currency:
        currency = business.default_currency

    if payload.price_amount is not None and currency is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="currency is required when price_amount is set",
        )

    product = Product(
        business_id=business_id,
        name=payload.name,
        description=payload.description,
        price_amount=payload.price_amount,
        currency=currency,
        status=ProductStatus.draft,
        source_type=ProductSourceType.manual,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)

@router.get("", response_model=list[ProductRead])
async def list_products(
    business_id: uuid.UUID,
    status_filter: Annotated[
        ProductStatus | None,
        Query(alias="status"),
    ] = None,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> list[ProductRead]:

    stmt = select(Product).where(Product.business_id == business_id)
    if status_filter is not None:
        stmt = stmt.where(Product.status == status_filter)
    stmt = stmt.order_by(Product.created_at.desc())

    result = await db.execute(stmt)
    products = result.scalars().all()
    return [ProductRead.model_validate(p) for p in products]

@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:

    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductRead.model_validate(product)

@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdate,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:

    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        ).with_for_update()
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    sent = payload.model_fields_set
    if "name" in sent and payload.name is not None:
        product.name = payload.name
    if "description" in sent:
        product.description = payload.description
    if "price_amount" in sent:
        product.price_amount = payload.price_amount
    if "currency" in sent:
        product.currency = payload.currency

    if product.status == ProductStatus.confirmed:
        product.status = ProductStatus.needs_review
        product.merchant_confirmed_at = None

    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)

@router.post("/{product_id}/confirm", response_model=ProductRead)
async def confirm_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member(MemberRole.owner)),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        ).with_for_update()
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.status == ProductStatus.archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived products cannot be confirmed",
        )
    product.status = ProductStatus.confirmed
    product.merchant_confirmed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)

@router.post("/{product_id}/archive", response_model=ProductRead)
async def archive_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member(MemberRole.owner)),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        ).with_for_update()
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if product.status == ProductStatus.archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already archived",
        )
    product.status = ProductStatus.archived
    product.merchant_confirmed_at = None
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.get("/{product_id}/variants", response_model=list[ProductVariantRead])
async def list_variants(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    member: BusinessMember = Depends(require_business_member()),
    db: AsyncSession = Depends(get_db),
) -> list[ProductVariantRead]:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    result = await db.execute(
        select(ProductVariant)
        .where(ProductVariant.product_id == product_id)
        .order_by(ProductVariant.created_at.asc())
    )
    variants = result.scalars().all()
    return [ProductVariantRead.model_validate(v) for v in variants]