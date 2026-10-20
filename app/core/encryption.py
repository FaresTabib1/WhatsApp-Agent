"""
Chiffrement symétrique pour les tokens OAuth stockés au repos.

Stratégie :
- En local (développement) : token chiffré avec Fernet, clé dans TOKEN_ENCRYPTION_KEY.
- En production : token stocké dans GCP Secret Manager, secret_ref contient le chemin.

Le token en clair ne doit jamais apparaître dans :
- les logs
- les réponses API
- le champ meta JSONB (uniquement token_encrypted y est stocké)
- les variables d'environnement non chiffrées en production

TOKEN_ENCRYPTION_KEY doit être une clé Fernet valide (base64 url-safe 32 bytes).
Générer avec : python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_token(plain_token: str) -> str:
    """Chiffre un token OAuth. Retourne une string base64 url-safe."""
    return _get_fernet().encrypt(plain_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Déchiffre un token OAuth.
    Lève ValueError si le token est invalide ou la clé incorrecte.
    """
    try:
        return _get_fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Token decryption failed — invalid key or corrupted data") from e
