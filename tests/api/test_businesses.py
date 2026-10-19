"""
Tests d'intégration légers pour les routes /businesses.
La session de base de données et l'utilisateur courant sont surchargés via dependency_overrides.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.business import Business
from app.models.business_member import BusinessMember, MemberRole
from app.models.user import User


@pytest.fixture
def test_user():
    user = User(email="merchant@example.com")
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def mock_db_session(test_user):
    session = AsyncMock()
    session.add = MagicMock()

    async def fake_refresh(instance):
        now = datetime.now(timezone.utc)
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now

    session.refresh.side_effect = fake_refresh

    # Résultat par défaut pour les vérifications de membership (require_business_member)
    fake_member = BusinessMember(
        business_id=uuid.uuid4(),
        user_id=test_user.id,
        role=MemberRole.owner,
    )
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = fake_member
    session.execute.return_value = result_mock

    return session


@pytest.fixture
def client(mock_db_session, test_user):
    async def override_get_db():
        yield mock_db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_create_business_success(client, mock_db_session):
    response = client.post("/businesses", json={"name": "Boutique Tunisienne"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Boutique Tunisienne"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert mock_db_session.add.call_count == 2
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


def test_create_business_empty_name(client):
    response = client.post("/businesses", json={"name": ""})
    assert response.status_code == 422


def test_create_business_missing_name(client):
    response = client.post("/businesses", json={})
    assert response.status_code == 422


def test_get_business_success(client, mock_db_session):
    business_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    mock_business = Business(name="Boutique Existante")
    mock_business.id = business_id
    mock_business.created_at = now
    mock_business.updated_at = now

    mock_db_session.get.return_value = mock_business

    response = client.get(f"/businesses/{business_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(business_id)
    assert data["name"] == "Boutique Existante"
    mock_db_session.get.assert_awaited_with(Business, business_id)


def test_get_business_not_found(client, mock_db_session):
    business_id = uuid.uuid4()
    mock_db_session.get.return_value = None

    response = client.get(f"/businesses/{business_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Business not found"
    mock_db_session.get.assert_awaited_with(Business, business_id)


def test_get_business_invalid_uuid(client):
    response = client.get("/businesses/invalid-uuid")
    assert response.status_code == 422


def test_create_business_unauthenticated_returns_401(mock_db_session):
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    unauthed_client = TestClient(app)
    response = unauthed_client.post("/businesses", json={"name": "Boutique"})
    assert response.status_code in (401, 403)
    app.dependency_overrides.clear()


def test_get_business_unauthenticated_returns_401(mock_db_session):
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    unauthed_client = TestClient(app)
    response = unauthed_client.get(f"/businesses/{uuid.uuid4()}")
    assert response.status_code in (401, 403)
    app.dependency_overrides.clear()

