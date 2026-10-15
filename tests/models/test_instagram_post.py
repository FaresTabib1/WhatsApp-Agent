"""
Tests unitaires pour le modèle InstagramPost.
Pas de connexion DB — vérification via l'inspecteur SQLAlchemy.
"""

import uuid

from sqlalchemy import inspect

import app.models.business      # noqa: F401
import app.models.connection    # noqa: F401
from app.models.instagram_post import ImportStatus, InstagramPost


# --- Enum : ImportStatus ---

def test_import_status_pending():
    assert ImportStatus.pending.value == "pending"


def test_import_status_processing():
    assert ImportStatus.processing.value == "processing"


def test_import_status_completed():
    assert ImportStatus.completed.value == "completed"


def test_import_status_failed():
    assert ImportStatus.failed.value == "failed"


# --- Schéma : colonnes ---

def test_instagram_post_table_name():
    assert InstagramPost.__tablename__ == "instagram_posts"


def test_instagram_post_has_id():
    assert "id" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_id_is_pk():
    assert inspect(InstagramPost).columns["id"].primary_key is True


def test_instagram_post_has_business_id():
    assert "business_id" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_business_id_not_nullable():
    assert inspect(InstagramPost).columns["business_id"].nullable is False


def test_instagram_post_has_connection_id():
    assert "connection_id" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_connection_id_not_nullable():
    assert inspect(InstagramPost).columns["connection_id"].nullable is False


def test_instagram_post_has_external_post_id():
    assert "external_post_id" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_external_post_id_not_nullable():
    assert inspect(InstagramPost).columns["external_post_id"].nullable is False


def test_instagram_post_has_caption():
    assert "caption" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_caption_nullable():
    assert inspect(InstagramPost).columns["caption"].nullable is True


def test_instagram_post_has_media_url():
    assert "media_url" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_media_url_nullable():
    assert inspect(InstagramPost).columns["media_url"].nullable is True


def test_instagram_post_has_permalink():
    assert "permalink" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_permalink_nullable():
    assert inspect(InstagramPost).columns["permalink"].nullable is True


def test_instagram_post_has_posted_at():
    assert "posted_at" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_posted_at_nullable():
    assert inspect(InstagramPost).columns["posted_at"].nullable is True


def test_instagram_post_has_import_status():
    assert "import_status" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_import_status_not_nullable():
    assert inspect(InstagramPost).columns["import_status"].nullable is False


def test_instagram_post_has_created_at():
    assert "created_at" in [c.key for c in inspect(InstagramPost).columns]


def test_instagram_post_no_updated_at():
    """instagram_posts n'a pas de updated_at — un post importé n'est pas modifié."""
    assert "updated_at" not in [c.key for c in inspect(InstagramPost).columns]


# --- Contrainte unique ---

def test_instagram_post_unique_constraint_connection_external():
    """Empêche le double import d'une publication pour une connexion donnée."""
    from app.core.database import Base
    import app.models.instagram_post  # noqa: F401

    table = Base.metadata.tables["instagram_posts"]
    uc_cols = [
        frozenset(c.name for c in uc.columns)
        for uc in table.constraints
        if hasattr(uc, "columns") and len(list(uc.columns)) > 0
    ]
    assert frozenset({"connection_id", "external_post_id"}) in uc_cols


# --- Instantiation ---

def test_instagram_post_instantiation_sets_id():
    post = InstagramPost(
        business_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        external_post_id="17854360229135492",
    )
    assert post.id is not None
    assert isinstance(post.id, uuid.UUID)


def test_instagram_post_default_import_status_is_pending():
    post = InstagramPost(
        business_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        external_post_id="17854360229135492",
    )
    assert post.import_status == ImportStatus.pending


def test_instagram_post_caption_defaults_none():
    post = InstagramPost(
        business_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        external_post_id="17854360229135492",
    )
    assert post.caption is None


def test_instagram_post_media_url_defaults_none():
    post = InstagramPost(
        business_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        external_post_id="17854360229135492",
    )
    assert post.media_url is None


def test_instagram_post_fields():
    bid = uuid.uuid4()
    cid = uuid.uuid4()
    post = InstagramPost(
        business_id=bid,
        connection_id=cid,
        external_post_id="ABC123",
        caption="Robe été #mode",
        permalink="https://www.instagram.com/p/ABC123/",
    )
    assert post.business_id == bid
    assert post.connection_id == cid
    assert post.external_post_id == "ABC123"
    assert post.caption == "Robe été #mode"
    assert post.permalink == "https://www.instagram.com/p/ABC123/"
