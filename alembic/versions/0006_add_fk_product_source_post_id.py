from typing import Sequence, Union
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_foreign_key(
        "fk_products_source_post_id",
        source_table="products",
        referent_table="instagram_posts",
        local_cols=["source_post_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

def downgrade() -> None:
    op.drop_constraint(
        "fk_products_source_post_id",
        table_name="products",
        type_="foreignkey",
    )
