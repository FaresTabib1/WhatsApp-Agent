"""
Tests unitaires pour app/core/security.py.
Pas de DB requise.
"""

import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# --- Password ---

def test_hash_password_returns_string():
    h = hash_password("secret123")
    assert isinstance(h, str)


def test_hash_password_is_not_plaintext():
    h = hash_password("secret123")
    assert h != "secret123"


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_wrong():
    h = hash_password("secret123")
    assert verify_password("wrong", h) is False


def test_hash_is_different_each_call():
    """bcrypt génère un salt différent à chaque appel."""
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 != h2


# --- JWT ---

def test_create_access_token_returns_string():
    token = create_access_token("some-user-id")
    assert isinstance(token, str)


def test_decode_access_token_returns_subject():
    token = create_access_token("user-123")
    sub = decode_access_token(token)
    assert sub == "user-123"


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not.a.token") is None


def test_decode_tampered_token_returns_none():
    token = create_access_token("user-123")
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None


def test_roundtrip_uuid_subject():
    import uuid
    uid = str(uuid.uuid4())
    token = create_access_token(uid)
    assert decode_access_token(token) == uid
