"""
Tests unitaires pour la protection CSRF OAuth (create/decode_oauth_state).
Pas de DB requise.
"""

import time
import uuid
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.security import (
    SECRET_KEY,
    ALGORITHM,
    create_oauth_state,
    decode_oauth_state,
)


def test_create_oauth_state_returns_string():
    state = create_oauth_state("biz-id", "user-id")
    assert isinstance(state, str)
    assert len(state) > 20


def test_decode_oauth_state_returns_correct_ids():
    biz_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    state = create_oauth_state(biz_id, user_id)
    data = decode_oauth_state(state)
    assert data is not None
    assert data.business_id == biz_id
    assert data.user_id == user_id


def test_decode_oauth_state_invalid_returns_none():
    assert decode_oauth_state("not.a.jwt") is None


def test_decode_oauth_state_wrong_purpose_returns_none():
    """Un access token ne peut pas être réutilisé comme state CSRF."""
    from app.core.security import create_access_token
    access_token = create_access_token("some-user-id")
    assert decode_oauth_state(access_token) is None


def test_decode_oauth_state_expired_returns_none():
    """Un state expiré est rejeté."""
    from datetime import datetime, timedelta, timezone
    payload = {
        "purpose": "instagram_oauth",
        "business_id": "biz-id",
        "user_id": "user-id",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_state = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    assert decode_oauth_state(expired_state) is None


def test_decode_oauth_state_missing_business_id_returns_none():
    from datetime import datetime, timedelta, timezone
    payload = {
        "purpose": "instagram_oauth",
        "user_id": "user-id",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    state = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    assert decode_oauth_state(state) is None


def test_decode_oauth_state_tampered_returns_none():
    state = create_oauth_state("biz-id", "user-id")
    tampered = state[:-5] + "XXXXX"
    assert decode_oauth_state(tampered) is None


def test_state_different_each_call():
    """Deux states pour le même business/user doivent être différents."""
    s1 = create_oauth_state("biz", "user")
    s2 = create_oauth_state("biz", "user")
    assert s1 != s2
