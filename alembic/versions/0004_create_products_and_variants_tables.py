from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    product_status = sa.Enum(
        "draft", "needs_review", "confirmed", "archived",
        name="product_status",
    )
    product_source_type = sa.Enum(
        "instagram", "manual",
        name="product_source_type",
    )
    availability_status = sa.Enum(
        "available", "unavailable", "unknown",
        name="availability_status",
    )
    product_status.create(op.get_bind(), checkfirst=True)
    product_source_type.create(op.get_bind(), checkfirst=True)
    availability_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "business_id",
            UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price_amount", sa.Integer, nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "needs_review", "confirmed", "archived",
                name="product_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "source_type",
            sa.Enum(
                "instagram", "manual",
                name="product_source_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_post_id", UUID(as_uuid=True), nullable=True),
        sa.Column("merchant_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_products_business_id", "products", ["business_id"])
    op.create_index("ix_products_status", "products", ["status"])

    op.create_table(
        "product_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("size", sa.String(100), nullable=True),
        sa.Column("color", sa.String(100), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("price_amount_override", sa.Integer, nullable=True),
        sa.Column(
            "availability_status",
            sa.Enum(
                "available", "unavailable", "unknown",
                name="availability_status",
                create_type=False,
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("stock_quantity", sa.Integer, nullable=True),
        sa.Column("merchant_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")

    op.drop_index("ix_products_status", table_name="products")
    op.drop_index("ix_products_business_id", table_name="products")
    op.drop_table("products")

    sa.Enum(name="availability_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="product_source_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="product_status").drop(op.get_bind(), checkfirst=True)
