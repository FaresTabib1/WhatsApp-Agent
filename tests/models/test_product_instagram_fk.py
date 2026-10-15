"""
Tests pour la FK composite products(source_post_id, business_id) → instagram_posts(id, business_id).

Stratégie : vérification via métadonnées SQLAlchemy uniquement (pas de connexion DB).
La contrainte DB réelle (rejet cross-tenant) ne peut être testée que contre
un vrai PostgreSQL — voir les tests marqués `requires_db` ci-dessous.
"""
import pytest

import app.models.business      # noqa: F401 — enregistre Business dans la métadata
import app.models.connection    # noqa: F401
import app.models.instagram_post  # noqa: F401
from app.core.database import Base
from app.models.instagram_post import InstagramPost
from app.models.product import Product


# ---------------------------------------------------------------------------
# Tests structurels (sans DB)
# ---------------------------------------------------------------------------

class TestInstagramPostUniqueConstraint:
    def test_unique_id_business_id_exists(self):
        """UNIQUE(id, business_id) doit exister sur instagram_posts — cible de la FK composite."""
        from sqlalchemy import UniqueConstraint
        table = Base.metadata.tables["instagram_posts"]
        uc_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
        assert "uq_instagram_posts_id_business_id" in uc_names

    def test_unique_id_business_id_covers_correct_columns(self):
        """La contrainte UNIQUE doit porter sur les colonnes (id, business_id)."""
        from sqlalchemy import UniqueConstraint
        table = Base.metadata.tables["instagram_posts"]
        uc = next(
            c for c in table.constraints
            if isinstance(c, UniqueConstraint) and c.name == "uq_instagram_posts_id_business_id"
        )
        col_names = {col.name for col in uc.columns}
        assert col_names == {"id", "business_id"}


class TestProductCompositeForeignKey:
    def test_composite_fk_exists(self):
        """ForeignKeyConstraint composite fk_products_source_post_composite doit exister."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        fkc_names = {
            c.name for c in table.constraints
            if isinstance(c, ForeignKeyConstraint)
        }
        assert "fk_products_source_post_composite" in fkc_names

    def test_composite_fk_covers_correct_local_columns(self):
        """La FK composite doit porter sur (source_post_id, business_id) côté products."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_products_source_post_composite"
        )
        local_cols = {col.name for col in fkc.columns}
        assert local_cols == {"source_post_id", "business_id"}

    def test_composite_fk_references_instagram_posts(self):
        """La FK composite doit référencer instagram_posts.id et instagram_posts.business_id."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_products_source_post_composite"
        )
        targets = {fk.target_fullname for fk in fkc.elements}
        assert "instagram_posts.id" in targets
        assert "instagram_posts.business_id" in targets

    def test_composite_fk_ondelete_restrict(self):
        """ON DELETE doit être RESTRICT (SET NULL impossibe sur FK composite sans PG 15+)."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        fkc = next(
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint) and c.name == "fk_products_source_post_composite"
        )
        assert fkc.ondelete.upper() == "RESTRICT"

    def test_source_post_id_fk_is_part_of_composite(self):
        """SQLAlchemy reflète automatiquement les FK des ForeignKeyConstraint au niveau colonne.
        On vérifie que la FK sur source_post_id provient bien de la contrainte composite
        (pas d'une FK simple indépendante dont le nom serait fk_products_source_post_id)."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        # La FK simple d'origine (0006) avait le nom "fk_products_source_post_id".
        # Elle ne doit plus exister.
        old_simple_fkc = [
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint)
            and c.name == "fk_products_source_post_id"
        ]
        assert old_simple_fkc == [], "La FK simple fk_products_source_post_id ne doit plus exister."

    def test_source_post_id_is_nullable(self):
        """source_post_id doit rester nullable (produit sans post source Instagram)."""
        table = Base.metadata.tables["products"]
        assert table.c["source_post_id"].nullable is True

    def test_no_simple_fk_to_instagram_posts_id(self):
        """Aucune FK simple source_post_id → instagram_posts.id ne doit subsister."""
        from sqlalchemy import ForeignKeyConstraint
        table = Base.metadata.tables["products"]
        # Cherche une contrainte FK portant uniquement sur source_post_id vers instagram_posts.id
        simple_fks = [
            c for c in table.constraints
            if isinstance(c, ForeignKeyConstraint)
            and {col.name for col in c.columns} == {"source_post_id"}
        ]
        assert simple_fks == [], "La FK simple fk_products_source_post_id ne doit plus exister dans le modèle."


class TestRelationships:
    def test_product_has_source_post_relationship(self):
        """Product doit exposer une relation SQLAlchemy vers InstagramPost."""
        mapper_attrs = [r.key for r in Product.__mapper__.relationships]
        assert "source_post" in mapper_attrs

    def test_instagram_post_has_products_relationship(self):
        """InstagramPost doit exposer la relation inverse vers Product."""
        mapper_attrs = [r.key for r in InstagramPost.__mapper__.relationships]
        assert "products" in mapper_attrs

    def test_source_post_relationship_not_duplicated(self):
        """La relation 'products' ne doit apparaître qu'une seule fois dans InstagramPost.__mapper__."""
        keys = [r.key for r in InstagramPost.__mapper__.relationships]
        assert keys.count("products") == 1


# ---------------------------------------------------------------------------
# Tests qui nécessitent un vrai PostgreSQL (non exécutés en CI sans DB)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Nécessite une connexion PostgreSQL réelle — exécuter manuellement avec la DB de test.")
def test_product_can_reference_post_from_same_business():
    """
    Un produit peut référencer une publication de SA PROPRE boutique.
    Scénario positif : INSERT réussi.

    Pour exécuter :
        DATABASE_URL=postgresql+asyncpg://... uv run pytest -k test_product_can_reference -s
    """
    # Implémentation à compléter avec une fixture de DB de test.
    pass


@pytest.mark.skip(reason="Nécessite une connexion PostgreSQL réelle — exécuter manuellement avec la DB de test.")
def test_product_cannot_reference_post_from_different_business():
    """
    Un produit NE PEUT PAS référencer une publication d'une AUTRE boutique.
    Scénario négatif : PostgreSQL doit lever une violation de FK.

    Pour exécuter :
        DATABASE_URL=postgresql+asyncpg://... uv run pytest -k test_product_cannot_reference -s
    """
    # Implémentation à compléter avec une fixture de DB de test.
    pass
