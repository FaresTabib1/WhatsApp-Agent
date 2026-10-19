import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import Base, get_db
from app.main import app
from app.models.product import AvailabilityStatus, Product, ProductVariant

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


# --- Helpers ---

async def _register_and_token(client, email="owner@test.com"):
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    return r.json()["access_token"]


async def _create_business(client, token, name="Boutique"):
    r = await client.post(
        "/businesses",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()


async def _create_product(client, token, business_id):
    r = await client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Robe été", "price_amount": 5000, "currency": "TND"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()


async def _add_variant(
    db_session: AsyncSession,
    product_id: uuid.UUID,
    size: str | None = "M",
    color: str | None = "Rouge",
    availability: AvailabilityStatus = AvailabilityStatus.unknown,
    price_override: int | None = None,
) -> ProductVariant:
    """Insère une variante directement en DB (les variantes sont créées par import Instagram)."""
    variant = ProductVariant(
        product_id=product_id,
        size=size,
        color=color,
        availability_status=availability,
        price_amount_override=price_override,
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)
    return variant


# --- Tests ---

@pytest.mark.asyncio
async def test_list_variants_empty_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_variants_returns_variants(client, db_session):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    await _add_variant(db_session, uuid.UUID(product["id"]), size="S", color="Bleu")
    await _add_variant(db_session, uuid.UUID(product["id"]), size="M", color="Rouge")

    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_variants_fields(client, db_session):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    await _add_variant(
        db_session, uuid.UUID(product["id"]),
        size="L", color="Vert", price_override=4500,
    )
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    v = r.json()[0]
    assert v["size"] == "L"
    assert v["color"] == "Vert"
    assert v["price_amount_override"] == 4500
    assert "product_id" in v
    assert "id" in v


@pytest.mark.asyncio
async def test_list_variants_availability_unknown_by_default(client, db_session):
    """
    Une variante sans disponibilité confirmée doit retourner unknown.
    Ne jamais interpréter unknown comme available.
    """
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    await _add_variant(
        db_session, uuid.UUID(product["id"]),
        availability=AvailabilityStatus.unknown,
    )
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()[0]["availability_status"] == "unknown"


@pytest.mark.asyncio
async def test_list_variants_merchant_confirmed_at_null(client, db_session):
    """Une variante non confirmée a merchant_confirmed_at=NULL."""
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    await _add_variant(db_session, uuid.UUID(product["id"]))
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()[0]["merchant_confirmed_at"] is None


@pytest.mark.asyncio
async def test_list_variants_unauthenticated_returns_403(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = await _create_product(client, token, biz["id"])
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_variants_non_member_returns_403(client):
    owner = await _register_and_token(client, "owner@test.com")
    other = await _register_and_token(client, "other@test.com")
    biz = await _create_business(client, owner)
    product = await _create_product(client, owner, biz["id"])
    r = await client.get(
        f"/businesses/{biz['id']}/products/{product['id']}/variants",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_variants_product_not_found_returns_404(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/businesses/{biz['id']}/products/{uuid.uuid4()}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_variants_cross_tenant_isolation(client, db_session):
    """
    Les variantes d'un produit d'une autre boutique retournent 404.
    Ne révèle pas l'existence d'un produit étranger.
    """
    owner_a = await _register_and_token(client, "a@test.com")
    owner_b = await _register_and_token(client, "b@test.com")
    biz_a = await _create_business(client, owner_a, "Boutique A")
    biz_b = await _create_business(client, owner_b, "Boutique B")
    product_b = await _create_product(client, owner_b, biz_b["id"])

    # owner_a tente d'accéder aux variantes du produit de boutique B
    r = await client.get(
        f"/businesses/{biz_a['id']}/products/{product_b['id']}/variants",
        headers={"Authorization": f"Bearer {owner_a}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_variants_only_own_product(client, db_session):
    """Les variantes retournées appartiennent uniquement au produit demandé."""
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product_a = await _create_product(client, token, biz["id"])
    product_b = await _create_product(client, token, biz["id"])

    await _add_variant(db_session, uuid.UUID(product_a["id"]), size="S")
    await _add_variant(db_session, uuid.UUID(product_b["id"]), size="XL")

    r = await client.get(
        f"/businesses/{biz['id']}/products/{product_a['id']}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    variants = r.json()
    assert len(variants) == 1
    assert variants[0]["size"] == "S"
    assert all(v["product_id"] == product_a["id"] for v in variants)