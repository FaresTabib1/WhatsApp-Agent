"""
Tests unitaires pour le modèle Connection.
Pas de connexion DB requise — vérification via l'inspecteur SQLAlchemy.
"""

import uuid

from sqlalchemy import inspect

import app.models.connection  # noqa: F401
from app.models.connection import Connection, ConnectionProvider, ConnectionStatus


# --- Enum tests ---

def test_connection_provider_has_instagram():
    assert ConnectionProvider.instagram.value == "instagram"


def test_connection_provider_has_whatsapp():
    assert ConnectionProvider.whatsapp.value == "whatsapp"


def test_connection_status_has_active():
    assert ConnectionStatus.active.value == "active"


def test_connection_status_has_inactive():
    assert ConnectionStatus.inactive.value == "inactive"


def test_connection_status_has_error():
    assert ConnectionStatus.error.value == "error"


# --- Schema tests ---

def test_connection_table_name():
    assert Connection.__tablename__ == "connections"


def test_connection_has_id_column():
    mapper = inspect(Connection)
    assert "id" in [col.key for col in mapper.columns]


def test_connection_id_is_primary_key():
    mapper = inspect(Connection)
    assert mapper.columns["id"].primary_key is True


def test_connection_has_business_id_column():
    mapper = inspect(Connection)
    assert "business_id" in [col.key for col in mapper.columns]


def test_connection_business_id_not_nullable():
    mapper = inspect(Connection)
    assert mapper.columns["business_id"].nullable is False


def test_connection_has_provider_column():
    mapper = inspect(Connection)
    assert "provider" in [col.key for col in mapper.columns]


def test_connection_provider_not_nullable():
    mapper = inspect(Connection)
    assert mapper.columns["provider"].nullable is False


def test_connection_has_provider_account_id_column():
    mapper = inspect(Connection)
    assert "provider_account_id" in [col.key for col in mapper.columns]


def test_connection_provider_account_id_not_nullable():
    mapper = inspect(Connection)
    assert mapper.columns["provider_account_id"].nullable is False


def test_connection_has_status_column():
    mapper = inspect(Connection)
    assert "status" in [col.key for col in mapper.columns]


def test_connection_status_not_nullable():
    mapper = inspect(Connection)
    assert mapper.columns["status"].nullable is False


def test_connection_has_metadata_column():
    mapper = inspect(Connection)
    assert "meta" in [col.key for col in mapper.columns]


def test_connection_metadata_is_nullable():
    mapper = inspect(Connection)
    assert mapper.columns["meta"].nullable is True


def test_connection_has_secret_ref_column():
    mapper = inspect(Connection)
    assert "secret_ref" in [col.key for col in mapper.columns]


def test_connection_secret_ref_is_nullable():
    """Référence Secret Manager — absente avant la première connexion OAuth."""
    mapper = inspect(Connection)
    assert mapper.columns["secret_ref"].nullable is True


def test_connection_has_created_at_column():
    mapper = inspect(Connection)
    assert "created_at" in [col.key for col in mapper.columns]


def test_connection_has_updated_at_column():
    mapper = inspect(Connection)
    assert "updated_at" in [col.key for col in mapper.columns]


def test_connection_unique_constraint_provider_account():
    """Un compte externe n'appartient qu'à une seule boutique."""
    from app.core.database import Base
    import app.models.connection  # noqa: F401

    table = Base.metadata.tables["connections"]
    uc_cols = [
        frozenset(c.name for c in uc.columns)
        for uc in table.constraints
        if hasattr(uc, "columns") and len(list(uc.columns)) > 0
    ]
    assert frozenset({"provider", "provider_account_id"}) in uc_cols


# --- Instantiation tests ---

def test_connection_instantiation_sets_id():
    conn = Connection(
        business_id=uuid.uuid4(),
        provider=ConnectionProvider.instagram,
        provider_account_id="123456789",
        status=ConnectionStatus.inactive,
    )
    assert conn.id is not None
    assert isinstance(conn.id, uuid.UUID)


def test_connection_instantiation_fields():
    bid = uuid.uuid4()
    conn = Connection(
        business_id=bid,
        provider=ConnectionProvider.whatsapp,
        provider_account_id="987654321",
        status=ConnectionStatus.active,
    )
    assert conn.business_id == bid
    assert conn.provider == ConnectionProvider.whatsapp
    assert conn.provider_account_id == "987654321"
    assert conn.status == ConnectionStatus.active


def test_connection_secret_ref_defaults_none():
    conn = Connection(
        business_id=uuid.uuid4(),
        provider=ConnectionProvider.instagram,
        provider_account_id="abc",
        status=ConnectionStatus.inactive,
    )
    assert conn.secret_ref is None


def test_connection_meta_defaults_none():
    conn = Connection(
        business_id=uuid.uuid4(),
        provider=ConnectionProvider.instagram,
        provider_account_id="abc",
        status=ConnectionStatus.inactive,
    )
    assert conn.meta is None
