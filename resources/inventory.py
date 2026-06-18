"""
Temu Open Platform API — Repository Stock / Inventaire

Actions référencées :
  bg.stock.list    — consultation du stock par SKU
  bg.stock.update  — mise à jour du stock

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import logging

from ..core.exceptions import NotFoundError
from ..http.client import TemuHTTPClient
from ..models import StockEntry

logger = logging.getLogger(__name__)


class InventoryRepository:
    """Accès au stock via l'API Temu."""

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    def get(self, sku: str) -> StockEntry:
        """Retourne le stock d'un SKU spécifique."""
        data    = self._http.call("bg.stock.list", {"sku_id": sku})
        entries = data.get("stock_list", [])
        if not entries:
            raise NotFoundError(f"SKU introuvable : {sku}")
        return StockEntry.from_api(entries[0])

    def get_many(self, skus: list[str]) -> list[StockEntry]:
        """Retourne le stock pour une liste de SKUs."""
        return [self.get(sku) for sku in skus]

    def update(self, sku: str, quantity: int, warehouse_id: str = "") -> bool:
        """Met à jour le stock disponible d'un SKU. Retourne True si succès."""
        params: dict = {"sku_id": sku, "available_stock": quantity}
        if warehouse_id:
            params["warehouse_id"] = warehouse_id

        data    = self._http.call("bg.stock.update", params)
        success = bool(data.get("success", False))
        if success:
            logger.info("stock_mis_a_jour", extra={"sku": sku, "quantite": quantity})
        else:
            logger.warning("stock_update_echec", extra={"sku": sku})
        return success
