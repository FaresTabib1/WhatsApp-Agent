import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.product import AvailabilityStatus, ProductStatus

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price_amount: int | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=10)


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price_amount: int | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=10)

    @model_validator(mode="after")
    def currency_required_if_price_set(self) -> "ProductUpdate":
        if (
            "price_amount" in self.model_fields_set
            and self.price_amount is not None
            and "currency" not in self.model_fields_set
            and self.currency is None
        ):
            raise ValueError("currency is required when price_amount is set")
        return self

class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    price_amount: int | None
    currency: str | None
    status: ProductStatus
    merchant_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    size: str | None
    color: str | None
    sku: str | None
    price_amount_override: int | None
    availability_status: AvailabilityStatus
    stock_quantity: int | None
    merchant_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime