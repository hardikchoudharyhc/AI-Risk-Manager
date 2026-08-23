from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CanonicalBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Customer(CanonicalBase):
    customer_id: str = Field(min_length=1)
    account_age_days: int | None = Field(default=None, ge=0)
    location: str | None = None
    account_created_at: datetime | None = None


class Order(CanonicalBase):
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    product_id: str | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    timestamp: datetime
    order_status: str | None = None
    delivery_status: str | None = None


class Transaction(CanonicalBase):
    transaction_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: str
    transaction_status: str
    timestamp: datetime


class Return(CanonicalBase):
    return_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    return_reason: str | None = None
    return_status: str
    timestamp: datetime


class Chargeback(CanonicalBase):
    chargeback_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    reason: str | None = None
    status: str
    timestamp: datetime


class Device(CanonicalBase):
    device_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    first_seen: datetime
    last_seen: datetime


class Address(CanonicalBase):
    address_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    location: str


CanonicalRecord = Customer | Order | Transaction | Return | Chargeback | Device | Address
RecordType = Literal["customer", "order", "transaction", "return", "chargeback", "device", "address"]