"""
Client Instagram Graph API.

Endpoint utilisé : GET /me/media
Scope requis     : instagram_business_basic
Host             : graph.instagram.com
Rate limit       : 200 appels/heure par utilisateur (Meta)

Champs autorisés par instagram_business_basic :
  id, caption, media_type, media_url, permalink, timestamp

Le token est déchiffré ici et ne doit jamais être logué ni retourné.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

_GRAPH_BASE = "https://graph.instagram.com"
_API_VERSION = "v21.0"
_MEDIA_FIELDS = "id,caption,media_type,media_url,permalink,timestamp"
_PAGE_SIZE = 25          # publications par page
_TIMEOUT_SECONDS = 30.0  # timeout réseau


@dataclass
class RawMediaItem:
    """Publication brute retournée par l'API Meta. Aucun champ inventé."""
    external_post_id: str
    caption: str | None
    media_type: str
    media_url: str | None     # peut être absent (vidéo avec audio sous droits)
    permalink: str | None
    posted_at: datetime | None


class MetaAPIError(Exception):
    """Erreur retournée par l'API Meta."""
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class TokenExpiredError(MetaAPIError):
    """Le token OAuth a expiré — reconnexion nécessaire."""
    pass


class RateLimitError(MetaAPIError):
    """Limite de 200 requêtes/heure atteinte."""
    pass


def _parse_posted_at(timestamp_str: str | None) -> datetime | None:
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def _check_meta_error(data: dict) -> None:
    """Analyse la réponse Meta et lève l'exception appropriée."""
    error = data.get("error", {})
    if not error:
        return
    code = error.get("code")
    message = error.get("message", "Unknown Meta API error")
    error_subcode = error.get("error_subcode")

    # Codes d'expiration de token Meta
    if code in (190, 102) or error_subcode in (460, 463, 467):
        raise TokenExpiredError(
            f"Instagram token expired or invalid (code={code}). "
            "The business owner must reconnect their Instagram account.",
            code=code,
        )
    # Rate limit
    if code == 4 or code == 17:
        raise RateLimitError(
            f"Meta API rate limit reached (code={code}). Retry after 1 hour.",
            code=code,
        )
    raise MetaAPIError(message, code=code)


async def iter_user_media(plain_token: str) -> AsyncIterator[RawMediaItem]:
    """
    Itère sur toutes les publications du compte Instagram connecté.
    Gère la pagination automatiquement via le curseur `after`.

    Paramètres :
      plain_token : token OAuth en clair (déchiffré par l'appelant)

    Lève :
      TokenExpiredError — token expiré, reconnexion nécessaire
      RateLimitError    — 200 req/h atteint
      MetaAPIError      — autre erreur Meta
      httpx.TimeoutException — timeout réseau
    """
    url = f"{_GRAPH_BASE}/{_API_VERSION}/me/media"
    params: dict = {
        "fields": _MEDIA_FIELDS,
        "limit": _PAGE_SIZE,
        "access_token": plain_token,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        while url:
            resp = await client.get(url, params=params)

            # Sur les pages suivantes, l'URL contient déjà les params
            params = {}

            if resp.status_code != 200:
                try:
                    data = resp.json()
                    _check_meta_error(data)
                except (ValueError, KeyError):
                    pass
                resp.raise_for_status()

            data = resp.json()
            _check_meta_error(data)

            for item in data.get("data", []):
                yield RawMediaItem(
                    external_post_id=item["id"],
                    caption=item.get("caption"),
                    media_type=item.get("media_type", "UNKNOWN"),
                    media_url=item.get("media_url"),   # absent si audio sous droits
                    permalink=item.get("permalink"),
                    posted_at=_parse_posted_at(item.get("timestamp")),
                )

            # Pagination : next contient l'URL complète avec le curseur
            paging = data.get("paging", {})
            url = paging.get("next")  # None si dernière page
