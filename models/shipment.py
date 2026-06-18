"""
Modèles de données — Expédition

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShipmentConfirmation:
    order_id:        str
    tracking_number: str
    carrier:         str
    success:         bool

    @classmethod
    def from_api(cls, order_id: str, data: dict) -> "ShipmentConfirmation":
        return cls(
            order_id        = order_id,
            tracking_number = data.get("tracking_number", ""),
            carrier         = data.get("logistics_company_name", ""),
            success         = data.get("result", False),
        )
