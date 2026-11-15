from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class PartySchema(BaseModel):
    name: str


class ProductSchema(BaseModel):
    name: str
    sku: str | None = None


class WarehouseSchema(BaseModel):
    name: str
    address: str


class OrderItemSchema(BaseModel):
    product: ProductSchema
    warehouse: WarehouseSchema | None = None
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderDataSchema(BaseModel):
    id: str
    order_number: str
    status: str
    created_at: datetime
    updated_at: datetime
    supplier: PartySchema | None = None
    buyer: PartySchema
    items_count: int
    total_amount: Decimal


class InvoiceGeneratePayload(BaseModel):
    order: OrderDataSchema
    items: list[OrderItemSchema] = Field(default_factory=list)
