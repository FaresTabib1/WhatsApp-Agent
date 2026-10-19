"""
Tests unitaires pour app/core/permissions.py.
Session mockée — pas de PostgreSQL requis.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core.permissions import _get_membership
from app.models.business import Business
from app.models.business_member import BusinessMember, MemberRole
from app.models.user import User


def _make_user() -> User:
    return User(email=f"{uuid.uuid4()}@test.com")


def _make_business() -> Business:
    return Business(name="Boutique Test")


def _make_member(business: Business, user: User, role: MemberRole) -> BusinessMember:
    m = BusinessMember(business_id=business.id, user_id=user.id, role=role)
    return m


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_membership_raises_404_when_business_not_found(mock_session):
    mock_session.get = AsyncMock(return_value=None)
    user = _make_user()

    with pytest.raises(HTTPException) as exc:
        await _get_membership(uuid.uuid4(), user, mock_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_membership_raises_403_when_not_member(mock_session):
    business = _make_business()
    user = _make_user()
    mock_session.get = AsyncMock(return_value=business)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc:
        await _get_membership(business.id, user, mock_session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_membership_returns_member_when_found(mock_session):
    business = _make_business()
    user = _make_user()
    member = _make_member(business, user, MemberRole.owner)

    mock_session.get = AsyncMock(return_value=business)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = member
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await _get_membership(business.id, user, mock_session)
    assert result is member


@pytest.mark.asyncio
async def test_get_membership_returns_member_role(mock_session):
    business = _make_business()
    user = _make_user()
    member = _make_member(business, user, MemberRole.member)

    mock_session.get = AsyncMock(return_value=business)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = member
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await _get_membership(business.id, user, mock_session)
    assert result.role == MemberRole.member
