from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.database as db_module


@pytest.fixture(autouse=True)
def reset_db_globals():
    orig_engine = db_module._engine
    orig_factory = db_module._session_factory
    db_module._engine = None
    db_module._session_factory = None
    yield
    db_module._engine = orig_engine
    db_module._session_factory = orig_factory


def test_missing_database_url_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL environment variable is not set"):
        db_module.get_engine()


def test_empty_database_url_raises_runtime_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL environment variable is not set"):
        db_module.get_engine()


def test_get_engine_reuses_singleton(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    mock_engine = MagicMock()

    with patch("app.core.database.create_async_engine", return_value=mock_engine) as mock_create:
        engine1 = db_module.get_engine()
        engine2 = db_module.get_engine()

        assert engine1 is mock_engine
        assert engine2 is mock_engine
        mock_create.assert_called_once_with(
            "postgresql+asyncpg://user:pass@localhost/db",
            echo=False,
            pool_pre_ping=True,
        )


def test_get_session_factory_reuses_singleton():
    mock_engine = MagicMock()
    mock_factory = MagicMock()

    with (
        patch("app.core.database.get_engine", return_value=mock_engine),
        patch("app.core.database.async_sessionmaker", return_value=mock_factory) as mock_sessionmaker,
    ):
        factory1 = db_module.get_session_factory()
        factory2 = db_module.get_session_factory()

        assert factory1 is mock_factory
        assert factory2 is mock_factory
        mock_sessionmaker.assert_called_once_with(
            mock_engine,
            class_=db_module.AsyncSession,
            expire_on_commit=False,
        )


@pytest.mark.asyncio
async def test_get_db_closes_session_on_success():
    mock_session = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_session_cm)

    with patch("app.core.database.get_session_factory", return_value=mock_factory):
        sessions = []
        async for session in db_module.get_db():
            sessions.append(session)

        assert sessions == [mock_session]
        mock_session_cm.__aenter__.assert_awaited_once()
        mock_session_cm.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_get_db_closes_session_on_exception():
    mock_session = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_session_cm)

    with patch("app.core.database.get_session_factory", return_value=mock_factory):
        gen = db_module.get_db()
        session = await anext(gen)
        assert session is mock_session

        with pytest.raises(ValueError, match="test error"):
            await gen.athrow(ValueError("test error"))

        mock_session_cm.__aenter__.assert_awaited_once()
        mock_session_cm.__aexit__.assert_awaited_once()
        call_args = mock_session_cm.__aexit__.await_args[0]
        assert call_args[0] is ValueError
