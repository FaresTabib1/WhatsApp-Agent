import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# --- POST /auth/register ---

@pytest.mark.asyncio
async def test_register_returns_201(client):
    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_returns_access_token(client):
    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@example.com", "password": "secret123"}
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client):
    response = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client):
    response = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "secret123"},
    )
    assert response.status_code == 422


# --- POST /auth/token ---

@pytest.mark.asyncio
async def test_login_returns_token(client):
    await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    response = await client.post(
        "/auth/token",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    response = await client.post(
        "/auth/token",
        json={"email": "user@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    response = await client.post(
        "/auth/token",
        json={"email": "ghost@example.com", "password": "secret123"},
    )
    assert response.status_code == 401


# --- Dépendance get_current_user ---

@pytest.mark.asyncio
async def test_protected_route_without_token_returns_403(client):
    """Sans token, les routes protégées retournent 403 (HTTPBearer default)."""
    response = await client.get("/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token_returns_401(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
