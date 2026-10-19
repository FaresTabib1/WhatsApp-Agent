"""add role to business_members

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-15

Rôles possibles : owner (propriétaire) et member (membre).
Nullable pour ne pas bloquer les lignes existantes sans rôle.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    member_role = sa.Enum("owner", "member", name="member_role")
    member_role.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "business_members",
        sa.Column(
            "role",
            sa.Enum("owner", "member", name="member_role", create_type=False),
            nullable=True,
            server_default="member",
        ),
    )


def downgrade() -> None:
    op.drop_column("business_members", "role")
    sa.Enum(name="member_role").drop(op.get_bind(), checkfirst=True)
