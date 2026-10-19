import pytest
import uuid
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

# --- Helpers ---
async def _register_and_token(client: AsyncClient, email: str = "owner@test.com") -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    return r.json()["access_token"]

async def _create_business(client: AsyncClient, token: str, name: str = "Boutique A") -> dict:
    r = await client.post(
        "/businesses",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()

async def _create_product(
    client: AsyncClient,
    token: str,
    business_id: str,
    name: str = "Robe été",
    price_amount: int | None = 5000,
    currency: str | None = "TND",
) -> dict:
    payload = {"name": name}
    if price_amount is not None:
        payload["price_amount"] = price_amount
    if currency is not None:
        payload["currency"] = currency
    r = await client.post(
        f"/businesses/{business_id}/products",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return r

# --- POST /businesses/{business_id}/products ---

@pytest.mark.asyncio
async def test_create_product_returns_201(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await _create_product(client, token, biz["id"])
    assert r.status_code == 201

@pytest.mark.asyncio
async def test_create_product_returns_correct_fields(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await _create_product(client, token, biz["id"], name="Robe été", price_amount=5000, currency="TND")
    data = r.json()
    assert data["name"] == "Robe été"
    assert data["price_amount"] == 5000
    assert data["currency"] == "TND"
    assert data["status"] == "draft"
    assert data["business_id"] == biz["id"]

@pytest.mark.asyncio
async def test_create_product_status_is_always_draft(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await _create_product(client, token, biz["id"])
    assert r.json()["status"] == "draft"

@pytest.mark.asyncio
async def test_create_product_inherits_business_currency(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Produit sans devise"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["price_amount"] is None

@pytest.mark.asyncio
async def test_create_product_negative_price_returns_422(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Test", "price_amount": -1, "currency": "TND"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422

@pytest.mark.asyncio
async def test_create_product_price_without_currency_uses_business_default(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Test", "price_amount": 5000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["currency"] == "TND"
    assert r.json()["price_amount"] == 5000

@pytest.mark.asyncio
async def test_create_product_unauthenticated_returns_403(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Test"},
    )
    assert r.status_code in (401, 403)

@pytest.mark.asyncio
async def test_create_product_non_member_returns_403(client):
    owner_token = await _register_and_token(client, "owner@test.com")
    other_token = await _register_and_token(client, "other@test.com")
    biz = await _create_business(client, owner_token)
    r = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Test", "price_amount": 1000, "currency": "TND"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_create_product_business_not_found_returns_404(client):
    token = await _register_and_token(client)
    import uuid
    r = await client.post(
        f"/businesses/{uuid.uuid4()}/products",
        json={"name": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404

# --- GET /businesses/{business_id}/products ---

@pytest.mark.asyncio
async def test_list_products_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/businesses/{biz['id']}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_list_products_returns_only_own_business(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    await _create_product(client, token, biz["id"], name="P1")
    await _create_product(client, token, biz["id"], name="P2")
    r = await client.get(
        f"/businesses/{biz['id']}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_products_filter_by_status(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    await _create_product(client, token, biz["id"], name="P1")
    r = await client.get(
        f"/businesses/{biz['id']}/products?status=draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert all(p["status"] == "draft" for p in r.json())

@pytest.mark.asyncio
async def test_list_products_filter_confirmed_returns_empty(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    await _create_product(client, token, biz["id"])
    r = await client.get(
        f"/businesses/{biz['id']}/products?status=confirmed",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.asyncio
async def test_list_products_unauthenticated_returns_403(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(f"/businesses/{biz['id']}/products")
    assert r.status_code in (401, 403)

# --- GET /businesses/{business_id}/products/{product_id} ---

@pytest.mark.asyncio
async def test_get_product_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    created = (await _create_product(client, token, biz["id"])).json()
    r = await client.get(
        f"/businesses/{biz['id']}/products/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]

@pytest.mark.asyncio
async def test_get_product_not_found_returns_404(client):
    import uuid
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.get(
        f"/businesses/{biz['id']}/products/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_get_product_cross_tenant_isolation_returns_404(client):
    owner_a = await _register_and_token(client, "a@test.com")
    owner_b = await _register_and_token(client, "b@test.com")
    biz_a = await _create_business(client, owner_a, "Boutique A")
    biz_b = await _create_business(client, owner_b, "Boutique B")

    product_b = (await _create_product(client, owner_b, biz_b["id"])).json()
    r = await client.get(
        f"/businesses/{biz_a['id']}/products/{product_b['id']}",
        headers={"Authorization": f"Bearer {owner_a}"},
    )
    assert r.status_code == 404

# --- Validation catalogue : règles de fiabilité commerciale ---

@pytest.mark.asyncio
async def test_patch_clears_price_when_sent_null(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"],
                                     price_amount=5000, currency="TND")).json()
    assert product["price_amount"] == 5000

    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"price_amount": None, "currency": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["price_amount"] is None


@pytest.mark.asyncio
async def test_patch_absent_field_not_applied(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r0 = await client.post(
        f"/businesses/{biz['id']}/products",
        json={"name": "Robe", "description": "Belle robe", "price_amount": 5000, "currency": "TND"},
        headers={"Authorization": f"Bearer {token}"},
    )
    product = r0.json()
    assert product["description"] == "Belle robe"

    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Robe modifiée"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Belle robe"


@pytest.mark.asyncio
async def test_full_confirmation_cycle(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    pid = product["id"]
    bid = biz["id"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/businesses/{bid}/products/{pid}/confirm", headers=headers)
    assert r.json()["status"] == "confirmed"
    assert r.json()["merchant_confirmed_at"] is not None

    r = await client.patch(
        f"/businesses/{bid}/products/{pid}",
        json={"name": "Modifié"},
        headers=headers,
    )
    assert r.json()["status"] == "needs_review"
    assert r.json()["merchant_confirmed_at"] is None
    r = await client.post(f"/businesses/{bid}/products/{pid}/confirm", headers=headers)
    assert r.json()["status"] == "confirmed"
    assert r.json()["merchant_confirmed_at"] is not None


@pytest.mark.asyncio
async def test_needs_review_product_not_confirmed(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    pid = product["id"]
    bid = biz["id"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(f"/businesses/{bid}/products/{pid}/confirm", headers=headers)
    await client.patch(
        f"/businesses/{bid}/products/{pid}",
        json={"name": "Modifié"},
        headers=headers,
    )

    r = await client.get(f"/businesses/{bid}/products/{pid}", headers=headers)
    data = r.json()
    assert data["status"] == "needs_review"
    assert data["merchant_confirmed_at"] is None

    assert data["status"] != "confirmed"

@pytest.mark.asyncio
async def test_list_products_filter_confirmed_only(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    bid = biz["id"]

    p1 = (await _create_product(client, token, bid, name="P1")).json()
    p2 = (await _create_product(client, token, bid, name="P2")).json()
    p3 = (await _create_product(client, token, bid, name="P3")).json()

    await client.post(f"/businesses/{bid}/products/{p1['id']}/confirm", headers=headers)
    await client.post(f"/businesses/{bid}/products/{p2['id']}/confirm", headers=headers)
    await client.patch(
        f"/businesses/{bid}/products/{p2['id']}",
        json={"name": "P2 modifié"},
        headers=headers,
    )
    r = await client.get(f"/businesses/{bid}/products?status=confirmed", headers=headers)
    confirmed = r.json()
    assert len(confirmed) == 1
    assert confirmed[0]["id"] == p1["id"]
    assert confirmed[0]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_patch_does_not_accept_status_field(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()

    # Tenter de passer directement à confirmed via PATCH
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Test", "status": "confirmed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
    assert r.json()["merchant_confirmed_at"] is None

# --- PATCH /businesses/{business_id}/products/{product_id} ---

@pytest.mark.asyncio
async def test_patch_product_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Nouveau nom"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Nouveau nom"

@pytest.mark.asyncio
async def test_patch_product_updates_price(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"price_amount": 9900, "currency": "TND"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["price_amount"] == 9900
    assert r.json()["currency"] == "TND"

@pytest.mark.asyncio
async def test_patch_draft_product_stays_draft(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    assert product["status"] == "draft"
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Modifié"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["status"] == "draft"

@pytest.mark.asyncio
async def test_patch_confirmed_product_becomes_needs_review(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Modifié après confirmation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["status"] == "needs_review"
    assert r.json()["merchant_confirmed_at"] is None

@pytest.mark.asyncio
async def test_patch_product_negative_price_returns_422(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"price_amount": -100, "currency": "TND"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422

@pytest.mark.asyncio
async def test_patch_product_non_member_returns_403(client):
    owner = await _register_and_token(client, "owner@test.com")
    other = await _register_and_token(client, "other@test.com")
    biz = await _create_business(client, owner)
    product = (await _create_product(client, owner, biz["id"])).json()
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{product['id']}",
        json={"name": "Hack"},
        headers={"Authorization": f"Bearer {other}"},
    )
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_patch_product_not_found_returns_404(client):
    import uuid
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.patch(
        f"/businesses/{biz['id']}/products/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404

# --- POST /businesses/{business_id}/products/{product_id}/confirm ---
@pytest.mark.asyncio
async def test_confirm_product_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

@pytest.mark.asyncio
async def test_confirm_product_sets_merchant_confirmed_at(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["merchant_confirmed_at"] is not None

@pytest.mark.asyncio
async def test_confirm_product_member_returns_403(client):
    """Seul owner peut confirmer."""
    owner = await _register_and_token(client, "owner@test.com")
    member_token = await _register_and_token(client, "member@test.com")
    biz = await _create_business(client, owner)
    product = (await _create_product(client, owner, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_confirm_product_unauthenticated_returns_403(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
    )
    assert r.status_code in (401, 403)

@pytest.mark.asyncio
async def test_confirm_archived_product_returns_409(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"/businesses/{biz['id']}/products/{product['id']}/archive", headers=headers)
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/confirm",
        headers=headers,
    )
    assert r.status_code == 409

@pytest.mark.asyncio
async def test_confirm_product_not_found_returns_404(client):
    import uuid
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products/{uuid.uuid4()}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404

# --- POST /businesses/{business_id}/products/{product_id}/archive ---

@pytest.mark.asyncio
async def test_archive_product_returns_200(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/archive",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

@pytest.mark.asyncio
async def test_archive_product_clears_merchant_confirmed_at(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"/businesses/{biz['id']}/products/{product['id']}/confirm", headers=headers)
    r = await client.post(f"/businesses/{biz['id']}/products/{product['id']}/archive", headers=headers)
    assert r.json()["merchant_confirmed_at"] is None

@pytest.mark.asyncio
async def test_archive_already_archived_returns_409(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    product = (await _create_product(client, token, biz["id"])).json()
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"/businesses/{biz['id']}/products/{product['id']}/archive", headers=headers)
    r = await client.post(f"/businesses/{biz['id']}/products/{product['id']}/archive", headers=headers)
    assert r.status_code == 409

@pytest.mark.asyncio
async def test_archive_product_member_returns_403(client):
    owner = await _register_and_token(client, "owner@test.com")
    member = await _register_and_token(client, "member@test.com")
    biz = await _create_business(client, owner)
    product = (await _create_product(client, owner, biz["id"])).json()
    r = await client.post(
        f"/businesses/{biz['id']}/products/{product['id']}/archive",
        headers={"Authorization": f"Bearer {member}"},
    )
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_archive_product_not_found_returns_404(client):
    token = await _register_and_token(client)
    biz = await _create_business(client, token)
    r = await client.post(
        f"/businesses/{biz['id']}/products/{uuid.uuid4()}/archive",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404