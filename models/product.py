"""
Modèles de données — Catalogue / Produits

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProductImage:
    url:     str
    is_main: bool = False

    @classmethod
    def from_api(cls, data: dict) -> "ProductImage":
        return cls(
            url     = data.get("image_url", ""),
            is_main = data.get("is_main_image", False),
        )


@dataclass
class ProductVariant:
    sku:        str
    price:      float
    stock:      int
    attributes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "ProductVariant":
        return cls(
            sku        = data.get("sku_id", ""),
            price      = float(data.get("price", 0)),
            stock      = int(data.get("stock", 0)),
            attributes = {
                attr.get("attr_name", ""): attr.get("attr_value", "")
                for attr in data.get("sku_attr_list", [])
            },
        )


@dataclass
class Product:
    product_id:  str
    name:        str
    status:      str
    category_id: str
    variants:    list[ProductVariant] = field(default_factory=list)
    images:      list[ProductImage]   = field(default_factory=list)
    description: str                  = ""

    @classmethod
    def from_api(cls, data: dict) -> "Product":
        return cls(
            product_id  = data.get("goods_id", ""),
            name        = data.get("goods_name", ""),
            status      = data.get("goods_status", ""),
            category_id = data.get("cat_id", ""),
            variants    = [ProductVariant.from_api(v) for v in data.get("sku_list", [])],
            images      = [ProductImage.from_api(i) for i in data.get("image_list", [])],
            description = data.get("goods_desc", ""),
        )
