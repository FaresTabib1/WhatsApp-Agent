"""
Tests unitaires pour le modèle Business.
Pas de connexion DB requise — on vérifie la définition des colonnes via l'inspecteur SQLAlchemy.
"""

import uuid

from sqlalchemy import inspect

from app.models.business import Business


def test_business_table_name():
    assert Business.__tablename__ == "businesses"


def test_business_has_id_column():
    mapper = inspect(Business)
    assert "id" in [col.key for col in mapper.columns]


def test_business_id_is_primary_key():
    mapper = inspect(Business)
    col = mapper.columns["id"]
    assert col.primary_key is True


def test_business_has_name_column():
    mapper = inspect(Business)
    assert "name" in [col.key for col in mapper.columns]


def test_business_name_not_nullable():
    mapper = inspect(Business)
    col = mapper.columns["name"]
    assert col.nullable is False


def test_business_has_created_at_column():
    mapper = inspect(Business)
    assert "created_at" in [col.key for col in mapper.columns]


def test_business_has_updated_at_column():
    mapper = inspect(Business)
    assert "updated_at" in [col.key for col in mapper.columns]


def test_business_instantiation_sets_id():
    business = Business(name="Boutique Test")
    assert business.id is not None
    assert isinstance(business.id, uuid.UUID)


def test_business_instantiation_with_name():
    business = Business(name="Ma Boutique")
    assert business.name == "Ma Boutique"
