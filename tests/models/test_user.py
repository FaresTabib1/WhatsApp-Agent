"""
Tests unitaires pour le modèle User.
Pas de connexion DB requise — vérification via l'inspecteur SQLAlchemy.
"""

import uuid

from sqlalchemy import inspect

from app.models.user import User


def test_user_table_name():
    assert User.__tablename__ == "users"


def test_user_has_id_column():
    mapper = inspect(User)
    assert "id" in [col.key for col in mapper.columns]


def test_user_id_is_primary_key():
    mapper = inspect(User)
    col = mapper.columns["id"]
    assert col.primary_key is True


def test_user_has_email_column():
    mapper = inspect(User)
    assert "email" in [col.key for col in mapper.columns]


def test_user_email_not_nullable():
    mapper = inspect(User)
    col = mapper.columns["email"]
    assert col.nullable is False


def test_user_email_is_unique():
    index_names = {idx.name for idx in User.__table__.indexes}
    assert "ix_users_email" in index_names
    email_index = next(idx for idx in User.__table__.indexes if idx.name == "ix_users_email")
    assert email_index.unique is True
    assert any(col.name == "email" for col in email_index.columns)


def test_user_has_created_at_column():
    mapper = inspect(User)
    assert "created_at" in [col.key for col in mapper.columns]


def test_user_has_updated_at_column():
    mapper = inspect(User)
    assert "updated_at" in [col.key for col in mapper.columns]


def test_user_instantiation_sets_id():
    user = User(email="test@example.com")
    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)


def test_user_instantiation_with_email():
    user = User(email="boutique@example.com")
    assert user.email == "boutique@example.com"
