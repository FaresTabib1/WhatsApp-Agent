"""
Tests pour InstagramImportService.
SQLite en mémoire + mocks httpx.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.encryption import encrypt_token
from app.models.connection import Connection, ConnectionProvider, ConnectionStatus
from app.models.instagram_post import ImportStatus, InstagramPost
from app.models.product import Product
from app.services.instagram_import_service import InstagramImportService

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)
    engine = create_async_engine(TEST_DB, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_connection(
    business_id: uuid.UUID,
    status: ConnectionStatus = ConnectionStatus.active,
    with_token: bool = True,
) -> Connection:
    meta = {}
    if with_token:
        meta["token_encrypted"] = encrypt_token("fake_plain_token")
    return Connection(
        business_id=business_id,
        provider=ConnectionProvider.instagram,
        provider_account_id="17841400000001",
        status=status,
        meta=meta if meta else None,
    )


def _make_raw_items(count: int = 2):
    from app.integrations.meta_instagram.client import RawMediaItem
    return [
        RawMediaItem(
            external_post_id=f"post_{i}",
            caption=f"Caption {i}",
            media_type="IMAGE",
            media_url=f"https://cdn.instagram.com/{i}.jpg",
            permalink=f"https://instagram.com/p/{i}",
            posted_at=None,
        )
        for i in range(count)
    ]


# --- Helpers async ---

async def _save(session, obj):
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


# --- Tests ---

@pytest.mark.asyncio
async def test_sync_creates_posts(db_session):
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))
    items = _make_raw_items(3)

    async def mock_iter(_token):
        for item in items:
            yield item

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        result = await service.sync_connection(conn.id, biz_id)

    assert result.created == 3
    assert result.skipped == 0
    assert result.total_fetched == 3
    assert result.error is None


@pytest.mark.asyncio
async def test_sync_idempotent(db_session):
    """Synchroniser deux fois ne crée pas de doublons."""
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))
    items = _make_raw_items(2)

    async def mock_iter(_token):
        for item in items:
            yield item

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        r1 = await service.sync_connection(conn.id, biz_id)
        r2 = await service.sync_connection(conn.id, biz_id)

    assert r1.created == 2
    assert r2.created == 0
    assert r2.skipped == 2


@pytest.mark.asyncio
async def test_sync_preserves_existing_posts(db_session):
    """Les publications déjà importées ne sont pas modifiées."""
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))

    # Insérer manuellement avec une caption différente
    existing = InstagramPost(
        business_id=biz_id,
        connection_id=conn.id,
        external_post_id="post_0",
        caption="Caption originale",
        import_status=ImportStatus.completed,
    )
    await _save(db_session, existing)

    async def mock_iter(_token):
        from app.integrations.meta_instagram.client import RawMediaItem
        yield RawMediaItem(
            external_post_id="post_0",
            caption="Nouvelle caption",
            media_type="IMAGE",
            media_url=None, permalink=None, posted_at=None,
        )

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        await service.sync_connection(conn.id, biz_id)

    result = await db_session.execute(
        select(InstagramPost).where(
            InstagramPost.connection_id == conn.id,
            InstagramPost.external_post_id == "post_0",
        )
    )
    post = result.scalar_one()
    assert post.caption == "Caption originale"  # non modifié
    assert post.import_status == ImportStatus.completed  # non modifié


@pytest.mark.asyncio
async def test_sync_no_products_created(db_session):
    """L'import ne crée jamais de produit automatiquement."""
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))

    async def mock_iter(_token):
        for item in _make_raw_items(3):
            yield item

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        await service.sync_connection(conn.id, biz_id)

    result = await db_session.execute(select(Product))
    products = result.scalars().all()
    assert len(products) == 0


@pytest.mark.asyncio
async def test_sync_token_expired_marks_connection_error(db_session):
    from app.integrations.meta_instagram.client import TokenExpiredError
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))

    async def mock_iter(_token):
        raise TokenExpiredError("Token expired", code=190)
        yield  # rend la fonction async generator

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        result = await service.sync_connection(conn.id, biz_id)

    assert result.token_expired is True
    assert result.error is not None

    await db_session.refresh(conn)
    assert conn.status == ConnectionStatus.error


@pytest.mark.asyncio
async def test_sync_rate_limited_returns_result(db_session):
    from app.integrations.meta_instagram.client import RateLimitError
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))

    async def mock_iter(_token):
        raise RateLimitError("Rate limit", code=4)
        yield

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        result = await service.sync_connection(conn.id, biz_id)

    assert result.rate_limited is True
    await db_session.refresh(conn)
    assert conn.status == ConnectionStatus.active  # pas marqué error


@pytest.mark.asyncio
async def test_sync_cross_tenant_isolation(db_session):
    """Une connexion d'un autre business retourne une erreur."""
    biz_a = uuid.uuid4()
    biz_b = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_a))

    service = InstagramImportService(session=db_session)
    result = await service.sync_connection(conn.id, biz_b)

    assert result.error is not None
    assert result.created == 0


@pytest.mark.asyncio
async def test_sync_inactive_connection_returns_error(db_session):
    biz_id = uuid.uuid4()
    conn = await _save(
        db_session,
        _make_connection(biz_id, status=ConnectionStatus.inactive),
    )
    service = InstagramImportService(session=db_session)
    result = await service.sync_connection(conn.id, biz_id)
    assert result.error is not None
    assert "reconnection" in result.error.lower()


@pytest.mark.asyncio
async def test_sync_missing_token_returns_error(db_session):
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id, with_token=False))
    service = InstagramImportService(session=db_session)
    result = await service.sync_connection(conn.id, biz_id)
    assert result.error is not None
    assert "token" in result.error.lower()


@pytest.mark.asyncio
async def test_sync_posts_have_correct_business_id(db_session):
    biz_id = uuid.uuid4()
    conn = await _save(db_session, _make_connection(biz_id))

    async def mock_iter(_token):
        for item in _make_raw_items(2):
            yield item

    with patch("app.services.instagram_import_service.iter_user_media", mock_iter):
        service = InstagramImportService(session=db_session)
        await service.sync_connection(conn.id, biz_id)

    result = await db_session.execute(select(InstagramPost))
    posts = result.scalars().all()
    assert all(p.business_id == biz_id for p in posts)
    assert all(p.connection_id == conn.id for p in posts)
