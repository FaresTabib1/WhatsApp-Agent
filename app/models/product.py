import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.instagram_post import InstagramPost

from app.core.database import Base


class ProductStatus(str, enum.Enum):
    draft = "draft"
    needs_review = "needs_review"
    confirmed = "confirmed"
    archived = "archived"


class ProductSourceType(str, enum.Enum):
    instagram = "instagram"
    manual = "manual"


class AvailabilityStatus(str, enum.Enum):
    available = "available"
    unavailable = "unavailable"
    unknown = "unknown"


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        Index("ix_products_business_id", "business_id"),
        Index("ix_products_status", "status"),
        ForeignKeyConstraint(
            ["source_post_id", "business_id"],
            ["instagram_posts.id", "instagram_posts.business_id"],
            ondelete="RESTRICT",
            name="fk_products_source_post_composite",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, default=None)

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.draft,
    )
    source_type: Mapped[ProductSourceType] = mapped_column(
        Enum(ProductSourceType, name="product_source_type"),
        nullable=False,
    )
    source_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
    )
    merchant_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(  # noqa: F821
        "Business",
        back_populates="products",
    )
    source_post: Mapped[Optional["InstagramPost"]] = relationship(
        "InstagramPost",
        primaryjoin="Product.source_post_id == InstagramPost.id",
        foreign_keys="[Product.source_post_id]",
        back_populates="products",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        if "status" not in kwargs:
            kwargs["status"] = ProductStatus.draft
        super().__init__(**kwargs)


class ProductVariant(Base):
    __tablename__ = "product_variants"

    __table_args__ = (
        Index("ix_product_variants_product_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    size: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    color: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    price_amount_override: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, name="availability_status"),
        nullable=False,
        default=AvailabilityStatus.unknown,
    )
    stock_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    merchant_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="variants",
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        if "availability_status" not in kwargs:
            kwargs["availability_status"] = AvailabilityStatus.unknown
        super().__init__(**kwargs)