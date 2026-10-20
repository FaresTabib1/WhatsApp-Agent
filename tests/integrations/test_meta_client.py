"""
Tests unitaires pour app/integrations/meta_instagram/client.py.
httpx entièrement mocké — pas d'appel réseau réel.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.meta_instagram.client import (
    MetaAPIError,
    RateLimitError,
    TokenExpiredError,
    _check_meta_error,
    _parse_posted_at,
    iter_user_media,
)


# --- _parse_posted_at ---

def test_parse_posted_at_iso():
    from datetime import timezone
    result = _parse_posted_at("2024-03-15T10:30:00+0000")
    assert result is not None
    assert result.tzinfo == timezone.utc


def test_parse_posted_at_none():
    assert _parse_posted_at(None) is None


def test_parse_posted_at_invalid():
    assert _parse_posted_at("not-a-date") is None


# --- _check_meta_error ---

def test_check_meta_error_no_error():
    _check_meta_error({"data": []})  # ne lève pas


def test_check_meta_error_token_expired_190():
    with pytest.raises(TokenExpiredError):
        _check_meta_error({"error": {"code": 190, "message": "Token expired"}})


def test_check_meta_error_token_expired_102():
    with pytest.raises(TokenExpiredError):
        _check_meta_error({"error": {"code": 102, "message": "Session expired"}})


def test_check_meta_error_rate_limit_4():
    with pytest.raises(RateLimitError):
        _check_meta_error({"error": {"code": 4, "message": "Rate limit"}})


def test_check_meta_error_rate_limit_17():
    with pytest.raises(RateLimitError):
        _check_meta_error({"error": {"code": 17, "message": "User request limit"}})


def test_check_meta_error_generic():
    with pytest.raises(MetaAPIError):
        _check_meta_error({"error": {"code": 999, "message": "Unknown error"}})


# --- iter_user_media ---

def _make_mock_client(pages: list[dict]):
    """Crée un mock httpx.AsyncClient retournant des pages successives."""
    responses = [
        MagicMock(
            status_code=200,
            json=lambda p=page: p,
            raise_for_status=lambda: None,
        )
        for page in pages
    ]
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=responses)
    return mock_client


@pytest.mark.asyncio
async def test_iter_user_media_single_page():
    page = {
        "data": [
            {"id": "111", "caption": "Post 1", "media_type": "IMAGE",
             "media_url": "https://example.com/1.jpg",
             "permalink": "https://instagram.com/p/111", "timestamp": "2024-01-01T10:00:00+0000"},
            {"id": "222", "caption": "Post 2", "media_type": "IMAGE",
             "media_url": "https://example.com/2.jpg",
             "permalink": "https://instagram.com/p/222", "timestamp": "2024-01-02T10:00:00+0000"},
        ],
        "paging": {},  # pas de next → fin
    }
    mock_client = _make_mock_client([page])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        items = [item async for item in iter_user_media("fake_token")]

    assert len(items) == 2
    assert items[0].external_post_id == "111"
    assert items[1].external_post_id == "222"


@pytest.mark.asyncio
async def test_iter_user_media_pagination():
    page1 = {
        "data": [{"id": "111", "media_type": "IMAGE"}],
        "paging": {"next": "https://graph.instagram.com/v21.0/me/media?after=CURSOR"},
    }
    page2 = {
        "data": [{"id": "222", "media_type": "IMAGE"}],
        "paging": {},  # fin
    }
    mock_client = _make_mock_client([page1, page2])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        items = [item async for item in iter_user_media("fake_token")]

    assert len(items) == 2
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_iter_user_media_empty():
    page = {"data": [], "paging": {}}
    mock_client = _make_mock_client([page])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        items = [item async for item in iter_user_media("fake_token")]
    assert items == []


@pytest.mark.asyncio
async def test_iter_user_media_token_expired():
    page = {"error": {"code": 190, "message": "Token expired"}}
    mock_client = _make_mock_client([page])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(TokenExpiredError):
            async for _ in iter_user_media("expired_token"):
                pass


@pytest.mark.asyncio
async def test_iter_user_media_rate_limit():
    page = {"error": {"code": 4, "message": "Rate limit"}}
    mock_client = _make_mock_client([page])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RateLimitError):
            async for _ in iter_user_media("fake_token"):
                pass


@pytest.mark.asyncio
async def test_iter_user_media_missing_optional_fields():
    """media_url peut être absent (vidéo avec audio sous droits)."""
    page = {
        "data": [
            {"id": "333", "media_type": "VIDEO",
             "permalink": "https://instagram.com/p/333"},
        ],
        "paging": {},
    }
    mock_client = _make_mock_client([page])
    with patch("app.integrations.meta_instagram.client.httpx.AsyncClient", return_value=mock_client):
        items = [item async for item in iter_user_media("fake_token")]

    assert items[0].media_url is None
    assert items[0].caption is None
