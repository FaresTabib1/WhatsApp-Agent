"""
Tests unitaires pour le modèle BusinessMember.
Pas de connexion DB requise — vérification via l'inspecteur SQLAlchemy.
"""

import uuid

from sqlalchemy import inspect

from app.models.business_member import BusinessMember


def test_business_member_table_name():
    assert BusinessMember.__tablename__ == "business_members"


def test_business_member_has_id_column():
    mapper = inspect(BusinessMember)
    assert "id" in [col.key for col in mapper.columns]


def test_business_member_id_is_primary_key():
    mapper = inspect(BusinessMember)
    col = mapper.columns["id"]
    assert col.primary_key is True


def test_business_member_has_business_id_column():
    mapper = inspect(BusinessMember)
    assert "business_id" in [col.key for col in mapper.columns]


def test_business_member_business_id_not_nullable():
    mapper = inspect(BusinessMember)
    col = mapper.columns["business_id"]
    assert col.nullable is False


def test_business_member_has_user_id_column():
    mapper = inspect(BusinessMember)
    assert "user_id" in [col.key for col in mapper.columns]


def test_business_member_user_id_not_nullable():
    mapper = inspect(BusinessMember)
    col = mapper.columns["user_id"]
    assert col.nullable is False


def test_business_member_has_created_at_column():
    mapper = inspect(BusinessMember)
    assert "created_at" in [col.key for col in mapper.columns]


def test_business_member_unique_constraint_exists():
    """Un utilisateur ne peut appartenir qu'une seule fois à une boutique."""
    from app.core.database import Base
    import app.models.business_member  # noqa: F401

    table = Base.metadata.tables["business_members"]
    constraint_columns = [
        frozenset(c.name for c in uc.columns)
        for uc in table.constraints
        if hasattr(uc, "columns") and len(list(uc.columns)) > 0
    ]
    assert frozenset({"business_id", "user_id"}) in constraint_columns


def test_business_member_instantiation():
    business_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = BusinessMember(business_id=business_id, user_id=user_id)
    assert member.id is not None
    assert member.business_id == business_id
    assert member.user_id == user_id
