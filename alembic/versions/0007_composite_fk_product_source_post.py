from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_instagram_posts_id_business_id",
        "instagram_posts",
        ["id", "business_id"],
    )

    op.drop_constraint(
        "fk_products_source_post_id",
        table_name="products",
        type_="foreignkey",
    )
   
    op.create_foreign_key(
        "fk_products_source_post_composite",
        source_table="products",
        referent_table="instagram_posts",
        local_cols=["source_post_id", "business_id"],
        remote_cols=["id", "business_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_source_post_composite",
        table_name="products",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_instagram_posts_id_business_id",
        table_name="instagram_posts",
        type_="unique",
    )

    op.create_foreign_key(
        "fk_products_source_post_id",
        source_table="products",
        referent_table="instagram_posts",
        local_cols=["source_post_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
