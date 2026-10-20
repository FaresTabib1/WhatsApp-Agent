"""
Intégration Meta — Instagram Business Login OAuth.

Endpoints officiels (2025) :
  Autorisation  : https://www.instagram.com/oauth/authorize
  Token court   : https://api.instagram.com/oauth/access_token
  Token long    : https://graph.instagram.com/access_token
  Refresh       : https://graph.instagram.com/refresh_access_token
  Me            : https://graph.instagram.com/me

Scope minimal pour import de publications : instagram_business_basic
"""

import os
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import httpx

# Comptes éligibles à l'Instagram Graph API
_ELIGIBLE_ACCOUNT_TYPES = {"BUSINESS", "CREATOR"}

_AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
_LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
_ME_URL = "https://graph.instagram.com/me"

# Scope minimal — ne demander que ce qui est nécessaire
_REQUIRED_SCOPE = "instagram_business_basic"


class InstagramTokenData(TypedDict):
    access_token: str          # token long-lived — NE PAS LOGGER
    ig_user_id: str
    account_type: str
    username: str
    token_expires_at: str      # ISO 8601 UTC


def build_authorize_url(state: str) -> str:
    """
    Construit l'URL d'autorisation Meta.
    Le `state` est un JWT signé contenant business_id + user_id (protection CSRF).
    """
    app_id = os.environ["INSTAGRAM_APP_ID"]
    redirect_uri = os.environ["INSTAGRAM_REDIRECT_URI"]

    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": _REQUIRED_SCOPE,
        "response_type": "code",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{_AUTHORIZE_URL}?{query}"


async def exchange_code_for_token(code: str) -> InstagramTokenData:
    """
    1. Échange le code contre un token court (1h).
    2. Échange immédiatement contre un token long (60j).
    3. Récupère ig_user_id et account_type via /me.
    4. Vérifie que le compte est éligible (BUSINESS ou CREATOR).

    Lève httpx.HTTPStatusError si Meta retourne une erreur.
    Lève ValueError si le compte n'est pas éligible.
    """
    app_id = os.environ["INSTAGRAM_APP_ID"]
    app_secret = os.environ["INSTAGRAM_APP_SECRET"]
    redirect_uri = os.environ["INSTAGRAM_REDIRECT_URI"]

    async with httpx.AsyncClient() as client:
        # Étape 1 — Token court
        resp = await client.post(
            _TOKEN_URL,
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        resp.raise_for_status()
        short_data = resp.json()
        short_token = short_data["access_token"]

        # Étape 2 — Token long (60 jours)
        resp = await client.get(
            _LONG_TOKEN_URL,
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": app_secret,
                "access_token": short_token,
            },
        )
        resp.raise_for_status()
        long_data = resp.json()
        long_token = long_data["access_token"]
        # expires_in est en secondes
        expires_in = int(long_data.get("expires_in", 5183944))  # ~60j par défaut
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Étape 3 — Récupérer ig_user_id et vérifier l'éligibilité
        resp = await client.get(
            _ME_URL,
            params={
                "fields": "id,username,account_type",
                "access_token": long_token,
            },
        )
        resp.raise_for_status()
        me_data = resp.json()

    ig_user_id = me_data["id"]
    account_type = me_data.get("account_type", "UNKNOWN").upper()
    username = me_data.get("username", "")

    # Étape 4 — Vérifier l'éligibilité
    if account_type not in _ELIGIBLE_ACCOUNT_TYPES:
        raise ValueError(
            f"Instagram account type '{account_type}' is not eligible for the Graph API. "
            f"A Business or Creator account is required. "
            f"Personal accounts cannot use the Instagram API."
        )

    return InstagramTokenData(
        access_token=long_token,   # chiffré par l'appelant avant stockage
        ig_user_id=ig_user_id,
        account_type=account_type,
        username=username,
        token_expires_at=expires_at.isoformat(),
    )


async def refresh_token(encrypted_token: str) -> InstagramTokenData:
    """
    Rafraîchit un token long-lived pour 60 jours supplémentaires.
    Accepte le token chiffré — le déchiffrement est fait ici.
    Lève ValueError si le token ne peut pas être déchiffré.
    """
    from app.core.encryption import decrypt_token

    plain_token = decrypt_token(encrypted_token)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _REFRESH_URL,
            params={
                "grant_type": "ig_refresh_token",
                "access_token": plain_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        expires_in = int(data.get("expires_in", 5183944))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Récupérer les infos du compte pour mettre à jour les métadonnées
        resp = await client.get(
            _ME_URL,
            params={
                "fields": "id,username,account_type",
                "access_token": new_token,
            },
        )
        resp.raise_for_status()
        me_data = resp.json()

    return InstagramTokenData(
        access_token=new_token,
        ig_user_id=me_data["id"],
        account_type=me_data.get("account_type", "UNKNOWN").upper(),
        username=me_data.get("username", ""),
        token_expires_at=expires_at.isoformat(),
    )
