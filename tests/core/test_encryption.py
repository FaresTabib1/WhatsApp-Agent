"""
Tests unitaires pour app/core/encryption.py.
Pas de DB requise.
"""

import os

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch):
    """Injecte une clé Fernet valide pour tous les tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)


def test_encrypt_returns_string():
    from app.core.encryption import encrypt_token
    result = encrypt_token("my_plain_token")
    assert isinstance(result, str)


def test_encrypted_is_not_plaintext():
    from app.core.encryption import encrypt_token
    result = encrypt_token("my_plain_token")
    assert "my_plain_token" not in result


def test_roundtrip():
    from app.core.encryption import decrypt_token, encrypt_token
    plain = "instagram_access_token_abc123"
    assert decrypt_token(encrypt_token(plain)) == plain


def test_encrypt_different_each_call():
    """Fernet utilise un IV aléatoire — deux chiffrements du même texte diffèrent."""
    from app.core.encryption import encrypt_token
    e1 = encrypt_token("same_token")
    e2 = encrypt_token("same_token")
    assert e1 != e2


def test_decrypt_wrong_key_raises():
    from app.core.encryption import encrypt_token
    encrypted = encrypt_token("token")
    # Changer la clé
    os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    from app.core.encryption import decrypt_token
    with pytest.raises(ValueError, match="decryption failed"):
        decrypt_token(encrypted)


def test_decrypt_tampered_raises():
    from app.core.encryption import decrypt_token, encrypt_token
    encrypted = encrypt_token("token")
    tampered = encrypted[:-5] + "XXXXX"
    with pytest.raises(ValueError):
        decrypt_token(tampered)


def test_missing_key_raises():
    os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
    # Forcer le rechargement du module
    import importlib
    import app.core.encryption as enc_module
    importlib.reload(enc_module)
    with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY"):
        enc_module.encrypt_token("test")
