import uuid

from sqlalchemy import inspect

import app.models.business  # noqa: F401 — requis pour résoudre la relation Business
from app.models.product import (
    AvailabilityStatus,
    Product,
    ProductSourceType,
    ProductStatus,
    ProductVariant,
)


# --- Enum : ProductStatus ---

def test_product_status_draft():
    assert ProductStatus.draft.value == "draft"


def test_product_status_needs_review():
    assert ProductStatus.needs_review.value == "needs_review"


def test_product_status_confirmed():
    assert ProductStatus.confirmed.value == "confirmed"


def test_product_status_archived():
    assert ProductStatus.archived.value == "archived"


# --- Enum : ProductSourceType ---

def test_product_source_type_instagram():
    assert ProductSourceType.instagram.value == "instagram"


def test_product_source_type_manual():
    assert ProductSourceType.manual.value == "manual"


# --- Enum : AvailabilityStatus ---

def test_availability_status_available():
    assert AvailabilityStatus.available.value == "available"


def test_availability_status_unavailable():
    assert AvailabilityStatus.unavailable.value == "unavailable"


def test_availability_status_unknown():
    """Une disponibilité inconnue ne doit jamais devenir 'available' par défaut."""
    assert AvailabilityStatus.unknown.value == "unknown"


# --- Product : schéma ---

def test_product_table_name():
    assert Product.__tablename__ == "products"


def test_product_has_id():
    assert "id" in [c.key for c in inspect(Product).columns]


def test_product_id_is_pk():
    assert inspect(Product).columns["id"].primary_key is True


def test_product_has_business_id():
    assert "business_id" in [c.key for c in inspect(Product).columns]


def test_product_business_id_not_nullable():
    assert inspect(Product).columns["business_id"].nullable is False


def test_product_has_name():
    assert "name" in [c.key for c in inspect(Product).columns]


def test_product_name_not_nullable():
    assert inspect(Product).columns["name"].nullable is False


def test_product_has_description():
    assert "description" in [c.key for c in inspect(Product).columns]


def test_product_description_nullable():
    assert inspect(Product).columns["description"].nullable is True


def test_product_has_price_amount():
    assert "price_amount" in [c.key for c in inspect(Product).columns]


def test_product_price_amount_nullable():
    """Prix inconnu reste NULL — jamais transformé en 0."""
    assert inspect(Product).columns["price_amount"].nullable is True


def test_product_has_currency():
    assert "currency" in [c.key for c in inspect(Product).columns]


def test_product_currency_nullable():
    assert inspect(Product).columns["currency"].nullable is True


def test_product_has_status():
    assert "status" in [c.key for c in inspect(Product).columns]


def test_product_status_not_nullable():
    assert inspect(Product).columns["status"].nullable is False


def test_product_has_source_type():
    assert "source_type" in [c.key for c in inspect(Product).columns]


def test_product_source_type_not_nullable():
    assert inspect(Product).columns["source_type"].nullable is False


def test_product_has_source_post_id():
    assert "source_post_id" in [c.key for c in inspect(Product).columns]


def test_product_source_post_id_nullable():
    assert inspect(Product).columns["source_post_id"].nullable is True


def test_product_has_merchant_confirmed_at():
    assert "merchant_confirmed_at" in [c.key for c in inspect(Product).columns]


def test_product_merchant_confirmed_at_nullable():
    assert inspect(Product).columns["merchant_confirmed_at"].nullable is True


def test_product_has_created_at():
    assert "created_at" in [c.key for c in inspect(Product).columns]


def test_product_has_updated_at():
    assert "updated_at" in [c.key for c in inspect(Product).columns]


# --- Product : instantiation ---

def test_product_instantiation_sets_id():
    p = Product(
        business_id=uuid.uuid4(),
        name="Robe été",
        status=ProductStatus.draft,
        source_type=ProductSourceType.instagram,
    )
    assert p.id is not None
    assert isinstance(p.id, uuid.UUID)


def test_product_default_status_is_draft():
    p = Product(
        business_id=uuid.uuid4(),
        name="Test",
        source_type=ProductSourceType.manual,
    )
    assert p.status == ProductStatus.draft


def test_product_price_amount_is_none_by_default():
    """Prix inconnu → NULL, jamais 0."""
    p = Product(
        business_id=uuid.uuid4(),
        name="Test",
        source_type=ProductSourceType.manual,
    )
    assert p.price_amount is None


def test_product_merchant_confirmed_at_is_none_by_default():
    p = Product(
        business_id=uuid.uuid4(),
        name="Test",
        source_type=ProductSourceType.manual,
    )
    assert p.merchant_confirmed_at is None


# --- ProductVariant : schéma ---

def test_product_variant_table_name():
    assert ProductVariant.__tablename__ == "product_variants"


def test_product_variant_has_id():
    assert "id" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_has_product_id():
    assert "product_id" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_product_id_not_nullable():
    assert inspect(ProductVariant).columns["product_id"].nullable is False


def test_product_variant_has_size():
    assert "size" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_size_nullable():
    assert inspect(ProductVariant).columns["size"].nullable is True


def test_product_variant_has_color():
    assert "color" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_color_nullable():
    assert inspect(ProductVariant).columns["color"].nullable is True


def test_product_variant_has_sku():
    assert "sku" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_sku_nullable():
    assert inspect(ProductVariant).columns["sku"].nullable is True


def test_product_variant_has_price_amount_override():
    assert "price_amount_override" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_price_override_nullable():
    """Prix override inconnu → NULL, jamais 0."""
    assert inspect(ProductVariant).columns["price_amount_override"].nullable is True


def test_product_variant_has_availability_status():
    assert "availability_status" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_availability_not_nullable():
    assert inspect(ProductVariant).columns["availability_status"].nullable is False


def test_product_variant_has_stock_quantity():
    assert "stock_quantity" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_stock_quantity_nullable():
    assert inspect(ProductVariant).columns["stock_quantity"].nullable is True


def test_product_variant_has_merchant_confirmed_at():
    assert "merchant_confirmed_at" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_merchant_confirmed_at_nullable():
    assert inspect(ProductVariant).columns["merchant_confirmed_at"].nullable is True


def test_product_variant_has_created_at():
    assert "created_at" in [c.key for c in inspect(ProductVariant).columns]


def test_product_variant_has_updated_at():
    assert "updated_at" in [c.key for c in inspect(ProductVariant).columns]


# --- ProductVariant : instantiation ---

def test_product_variant_instantiation_sets_id():
    v = ProductVariant(
        product_id=uuid.uuid4(),
        availability_status=AvailabilityStatus.unknown,
    )
    assert v.id is not None
    assert isinstance(v.id, uuid.UUID)


def test_product_variant_default_availability_is_unknown():
    """Une disponibilité non renseignée reste 'unknown', jamais 'available'."""
    v = ProductVariant(product_id=uuid.uuid4())
    assert v.availability_status == AvailabilityStatus.unknown


def test_product_variant_price_override_defaults_none():
    v = ProductVariant(product_id=uuid.uuid4())
    assert v.price_amount_override is None


def test_product_variant_stock_quantity_defaults_none():
    v = ProductVariant(product_id=uuid.uuid4())
    assert v.stock_quantity is None
