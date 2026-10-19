"""add hashed_password to users

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-15

Ajoute hashed_password pour l'authentification JWT locale.
Nullable pour ne pas bloquer les lignes existantes.
La valeur NULL signifie que l'utilisateur n'a pas encore défini de mot de passe.
Migration vers Supabase Auth : cette colonne deviendra inutilisée
quand get_current_user() validera les JWT Supabase.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
