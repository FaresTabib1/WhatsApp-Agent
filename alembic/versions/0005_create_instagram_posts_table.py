from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import_status_enum = sa.Enum(
        "pending", "processing", "completed", "failed",
        name="import_status",
    )
    import_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "instagram_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "business_id",
            UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_post_id", sa.String(255), nullable=False),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("media_url", sa.String(2048), nullable=True),
        sa.Column("permalink", sa.String(2048), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "import_status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="import_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "connection_id",
            "external_post_id",
            name="uq_instagram_posts_connection_external",
        ),
    )
    op.create_index("ix_instagram_posts_business_id", "instagram_posts", ["business_id"])
    op.create_index("ix_instagram_posts_connection_id", "instagram_posts", ["connection_id"])
    op.create_index("ix_instagram_posts_external_post_id", "instagram_posts", ["external_post_id"])


def downgrade() -> None:
    op.drop_index("ix_instagram_posts_external_post_id", table_name="instagram_posts")
    op.drop_index("ix_instagram_posts_connection_id", table_name="instagram_posts")
    op.drop_index("ix_instagram_posts_business_id", table_name="instagram_posts")
    op.drop_table("instagram_posts")
    sa.Enum(name="import_status").drop(op.get_bind(), checkfirst=True)
