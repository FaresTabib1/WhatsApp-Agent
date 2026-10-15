"""
Tests pour la FK composite instagram_posts(connection_id, business_id) → connections(id, business_id).

Stratégie : vérification via métadonnées SQLAlchemy (pas de connexion DB requise pour les tests structurels).
"""
import pytest

import app.models.business  # noqa: F401
import app.models.connection  # noqa: F401
import app.models.instagram_post  # noqa: F401
from app.core.database import Base
from app.models.connection import Connection
from app.models.instagram_post import InstagramPost


# ---------------------------------------------------------------------------
# Tests structurels (sans DB)
# ---------------------------------------------------------------------------

class TestConnectionUniqueConstraint:
    def test_unique_id_business_id_exists(self):
        """UNIQUE(id, business_id) doit exister sur connections — cible de la FK composite."""
        from sqlalchemy import UniqueConstraint
        table = Base.metadata.tables["connections"]
        uc_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
        assert "uq_connections_id_business_id" in uc_names

    def test_unique_id_business_id_covers_correct_columns(self):
        """La contrainte UNIQUE doit porter sur les colonnes (id, business_id)."""
        from sqlalchemy import UniqueConstraint
        table = Base.metadata.tables["connections"]
        uc = next(
            c for c in table.constraints
            if isinstance(c, UniqueConstraint) and c.name == "uq_connections_id_business_id"
        )
        col_names = {col.name for col in uc.columns}
        assert col_names == {"id", "business_id"}


class TestInstagramPostCompositeForeignKey:
    def test_composite_fk_exists(self):
        """ForeignKeyConstraint composite fk_instagram_posts_connection_composite doit exister."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["instagram_posts"]
        fkc_names = {
            c.name for c in table.constraints
            if isinstance(c, ForeignKeyConstraint)
        }
        assert "fk_instagram_posts_connection_composite" in fkc_names

    def test_composite_fk_covers_correct_local_columns(self):
        """La FK composite doit porter sur (connection_id, business_id) côté instagram_posts."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["instagram_posts"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_instagram_posts_connection_composite"
        )
        local_cols = {col.name for col in fkc.columns}
        assert local_cols == {"connection_id", "business_id"}

    def test_composite_fk_references_connections(self):
        """La FK composite doit référencer connections.id et connections.business_id."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["instagram_posts"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_instagram_posts_connection_composite"
        )
        referred_table = fkc.referred_table.name
        referred_cols = {elem.column.name for elem in fkc.elements}
        assert referred_table == "connections"
        assert referred_cols == {"id", "business_id"}

    def test_composite_fk_ondelete_cascade(self):
        """La FK composite doit avoir ON DELETE CASCADE."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["instagram_posts"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_instagram_posts_connection_composite"
        )
        assert fkc.ondelete.upper() == "CASCADE"

    def test_no_simple_fk_to_connections_id(self):
        """Aucune FK simple connection_id → connections.id ne doit subsister."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["instagram_posts"]
        simple_fks = [
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint)
            and {col.name for col in c.columns} == {"connection_id"}
        ]
        assert simple_fks == [], "La FK simple vers connections.id ne doit plus exister dans le modèle."


class TestRelationships:
    def test_connection_has_instagram_posts_relationship(self):
        """Connection doit exposer la relation vers InstagramPost."""
        mapper_attrs = [r.key for r in Connection.__mapper__.relationships]
        assert "instagram_posts" in mapper_attrs

    def test_instagram_post_has_connection_relationship(self):
        """InstagramPost doit exposer la relation vers Connection."""
        mapper_attrs = [r.key for r in InstagramPost.__mapper__.relationships]
        assert "connection" in mapper_attrs

    def test_connection_relationship_not_duplicated(self):
        """La relation 'instagram_posts' ne doit apparaître qu'une seule fois dans Connection.__mapper__."""
        keys = [r.key for r in Connection.__mapper__.relationships]
        assert keys.count("instagram_posts") == 1

    def test_connection_instagram_posts_has_passive_deletes(self):
        """La relation Connection.instagram_posts doit avoir passive_deletes=True pour respecter ON DELETE CASCADE en DB."""
        rel = Connection.__mapper__.relationships["instagram_posts"]
        assert rel.passive_deletes is True


# ---------------------------------------------------------------------------
# Tests d'intégration réels (réservés à l'exécution PostgreSQL)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Nécessite une connexion PostgreSQL réelle après application de la migration 0008.")
def test_post_can_reference_connection_from_same_business():
    """Une publication peut référencer une connexion de SA PROPRE boutique (INSERT réussi)."""
    pass


@pytest.mark.skip(reason="Nécessite une connexion PostgreSQL réelle après application de la migration 0008.")
def test_post_cannot_reference_connection_from_different_business():
    """Une publication NE PEUT PAS référencer une connexion d'une AUTRE boutique (rejet FK 23503)."""
    pass


@pytest.mark.skip(reason="Nécessite une connexion PostgreSQL réelle après application de la migration 0008.")
def test_cascade_delete_connection_deletes_post():
    """La suppression d'une connexion supprime en cascade ses publications associées."""
    pass
