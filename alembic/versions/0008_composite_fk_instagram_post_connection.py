from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Contrainte UNIQUE composite sur connections(id, business_id)
    #    Requise comme cible de la clé étrangère composite.
    op.create_unique_constraint(
        "uq_connections_id_business_id",
        "connections",
        ["id", "business_id"],
    )

    # 2. Suppression de la clé étrangère simple connection_id → connections.id
    op.drop_constraint(
        "instagram_posts_connection_id_fkey",
        table_name="instagram_posts",
        type_="foreignkey",
    )

    # 3. Ajout de la clé étrangère composite (connection_id, business_id)
    #    → connections(id, business_id) avec ON DELETE CASCADE
    op.create_foreign_key(
        "fk_instagram_posts_connection_composite",
        source_table="instagram_posts",
        referent_table="connections",
        local_cols=["connection_id", "business_id"],
        remote_cols=["id", "business_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # 1. Suppression de la clé étrangère composite
    op.drop_constraint(
        "fk_instagram_posts_connection_composite",
        table_name="instagram_posts",
        type_="foreignkey",
    )

    # 2. Suppression de la contrainte UNIQUE composite
    op.drop_constraint(
        "uq_connections_id_business_id",
        table_name="connections",
        type_="unique",
    )

    # 3. Restauration de la clé étrangère simple avec ON DELETE CASCADE
    op.create_foreign_key(
        "instagram_posts_connection_id_fkey",
        source_table="instagram_posts",
        referent_table="connections",
        local_cols=["connection_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
