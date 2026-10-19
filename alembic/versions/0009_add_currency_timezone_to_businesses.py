from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "default_currency",
            sa.String(10),
            nullable=True,
            server_default="TND",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "timezone",
            sa.String(64),
            nullable=True,
            server_default="Africa/Tunis",
        ),
    )

def downgrade() -> None:
    op.drop_column("businesses", "timezone")
    op.drop_column("businesses", "default_currency")
