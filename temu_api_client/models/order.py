"""
Modèles de données — Commandes

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Address:
    recipient:    str
    phone:        str
    street:       str
    city:         str
    postal_code:  str
    country_code: str
    region:       str = ""

    @classmethod
    def from_api(cls, data: dict) -> "Address":
        return cls(
            recipient    = data.get("receiver_name", ""),
            phone        = data.get("receiver_phone", ""),
            street       = data.get("receiver_address", ""),
            city         = data.get("receiver_city", ""),
            postal_code  = data.get("receiver_zip", ""),
            country_code = data.get("receiver_country", ""),
            region       = data.get("receiver_state", ""),
        )


@dataclass
class OrderItem:
    sku:          str
    quantity:     int
    unit_price:   float
    product_name: str
    product_id:   str

    @classmethod
    def from_api(cls, data: dict) -> "OrderItem":
        return cls(
            sku          = data.get("sku_id", ""),
            quantity     = int(data.get("quantity", 0)),
            unit_price   = float(data.get("item_price", 0)),
            product_name = data.get("goods_name", ""),
            product_id   = data.get("goods_id", ""),
        )


@dataclass
class Order:
    order_id:         str
    status:           str
    created_at:       datetime
    updated_at:       datetime
    total_amount:     float
    currency:         str
    shipping_address: Address
    items:            list[OrderItem]     = field(default_factory=list)
    tracking_number:  str | None          = None

    @classmethod
    def from_api(cls, data: dict) -> "Order":
        return cls(
            order_id         = data.get("order_sn", ""),
            status           = data.get("order_status", ""),
            created_at       = datetime.fromtimestamp(data.get("create_time", 0)),
            updated_at       = datetime.fromtimestamp(data.get("update_time", 0)),
            total_amount     = float(data.get("total_amount", 0)),
            currency         = data.get("currency", "EUR"),
            shipping_address = Address.from_api(data.get("address_info", {})),
            items            = [OrderItem.from_api(i) for i in data.get("item_list", [])],
            tracking_number  = data.get("tracking_number"),
        )
