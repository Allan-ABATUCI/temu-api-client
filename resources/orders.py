"""
Temu Open Platform API — Repository Commandes

Actions référencées :
  bg.order.list    — liste paginée
  bg.order.detail  — détail d'une commande

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

from datetime import datetime
import logging

from ..core.exceptions import TemuAPIError
from ..http.client import TemuHTTPClient
from ..models import Order

logger = logging.getLogger(__name__)


class OrderRepository:
    """Accès aux commandes via l'API Temu."""

    STATUS_LABELS = {
        "0": "en_attente",
        "1": "payee",
        "2": "expediee",
        "3": "livree",
        "4": "annulee",
        "5": "remboursee",
    }

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    def list(
        self,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Order], bool]:
        """Retourne (orders, has_more)."""
        params: dict = {"page_no": page, "page_size": page_size}
        if status:
            params["order_status"] = status
        if start_date:
            params["start_time"] = int(start_date.timestamp() * 1000)
        if end_date:
            params["end_time"] = int(end_date.timestamp() * 1000)

        data     = self._http.call("bg.order.list", params)
        raw_list = data.get("order_list", [])
        has_more = data.get("has_more", False)
        orders   = [Order.from_api(o) for o in raw_list]

        logger.debug("commandes_recues", extra={"page": page, "count": len(orders)})
        return orders, has_more

    def get(self, order_id: str) -> Order:
        """Retourne le détail complet d'une commande."""
        data       = self._http.call("bg.order.detail", {"order_sn": order_id})
        order_data = data.get("order_info")
        if order_data is None:
            raise TemuAPIError(
                f"Champ 'order_info' absent de la réponse pour la commande {order_id}",
                error_code="MISSING_FIELD",
            )
        return Order.from_api(order_data)

    def list_all(
        self,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page_size: int = 50,
        max_pages: int = 100,
    ) -> list[Order]:
        """Itère automatiquement sur toutes les pages."""
        results: list[Order] = []
        for page in range(1, max_pages + 1):
            items, has_more = self.list(
                status=status, start_date=start_date,
                end_date=end_date, page=page, page_size=page_size,
            )
            results.extend(items)
            if not has_more:
                break
            if page == max_pages:
                logger.warning("pagination_tronquee", extra={"max_pages": max_pages})
        return results
