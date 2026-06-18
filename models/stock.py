"""
Modèles de données — Stock / Inventaire

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StockEntry:
    sku:           str
    available_qty: int
    reserved_qty:  int
    warehouse_id:  str

    @classmethod
    def from_api(cls, data: dict) -> "StockEntry":
        return cls(
            sku           = data.get("sku_id", ""),
            available_qty = int(data.get("available_stock", 0)),
            reserved_qty  = int(data.get("reserved_stock", 0)),
            warehouse_id  = data.get("warehouse_id", ""),
        )
