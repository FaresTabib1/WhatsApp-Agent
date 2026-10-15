from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Créer les types enum PostgreSQL
    connection_provider = sa.Enum(
        "instagram", "whatsapp",
        name="connection_provider",
    )
    connection_status = sa.Enum(
        "active", "inactive", "error",
        name="connection_status",
    )
    connection_provider.create(op.get_bind(), checkfirst=True)
    connection_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "business_id",
            UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.Enum("instagram", "whatsapp", name="connection_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "error", name="connection_status", create_type=False),
            nullable=False,
            server_default="inactive",
        ),
        sa.Column("secret_ref", sa.String(512), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
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
        sa.UniqueConstraint(
            "provider", "provider_account_id",
            name="uq_connections_provider_account",
        ),
    )
    op.create_index("ix_connections_business_id", "connections", ["business_id"])
    op.create_index("ix_connections_provider_account_id", "connections", ["provider_account_id"])


def downgrade() -> None:
    op.drop_index("ix_connections_provider_account_id", table_name="connections")
    op.drop_index("ix_connections_business_id", table_name="connections")
    op.drop_table("connections")

    sa.Enum(name="connection_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="connection_provider").drop(op.get_bind(), checkfirst=True)
