"""
Temu Open Platform API — Repository Commandes

Actions :
  bg.order.list.v2.get          — liste paginée des parent orders
  bg.order.detail.v2.get        — détail d'une commande
  bg.order.shippinginfo.v2.get  — adresse de livraison
"""

from __future__ import annotations

from datetime import datetime
import logging

from ..http.client import TemuHTTPClient
from ..models.order import ParentOrder

logger = logging.getLogger(__name__)


class OrderRepository:
    """Accès aux commandes via l'API Temu."""

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    def list(
        self,
        status: int | None = None,
        update_start: datetime | None = None,
        update_end: datetime | None = None,
        create_after: datetime | None = None,
        create_before: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ParentOrder], int]:
        """Retourne (orders, total_count)."""
        request: dict = {
            "pageNumber": page,
            "pageSize": min(page_size, 100),
        }
        if status is not None:
            request["parentOrderStatus"] = status
        if update_start:
            request["updateAtStart"] = int(update_start.timestamp())
        if update_end:
            request["updateAtEnd"] = int(update_end.timestamp())
        if create_after:
            request["createAfter"] = int(create_after.timestamp())
        if create_before:
            request["createBefore"] = int(create_before.timestamp())

        data = self._http.call("bg.order.list.v2.get", request)
        page_items = data.get("pageItems", [])
        total = int(data.get("totalItemNum", 0))
        orders = [ParentOrder.from_api(item) for item in page_items]

        logger.debug("orders_received", extra={"page": page, "count": len(orders), "total": total})
        return orders, total

    def get(self, parent_order_sn: str) -> ParentOrder:
        """Retourne le détail d'un parent order."""
        data = self._http.call("bg.order.detail.v2.get", {
            "parentOrderSn": parent_order_sn,
        })
        return ParentOrder.from_api(data)

    def get_shipping_info(self, parent_order_sn: str) -> dict:
        """Retourne l'adresse de livraison d'une commande."""
        return self._http.call("bg.order.shippinginfo.v2.get", {
            "parentOrderSn": parent_order_sn,
        })

    def list_all(
        self,
        status: int | None = None,
        update_start: datetime | None = None,
        update_end: datetime | None = None,
        create_after: datetime | None = None,
        create_before: datetime | None = None,
        page_size: int = 100,
        max_pages: int = 200,
    ) -> list[ParentOrder]:
        """Itère automatiquement sur toutes les pages."""
        results: list[ParentOrder] = []
        for page in range(1, max_pages + 1):
            items, total = self.list(
                status=status,
                update_start=update_start,
                update_end=update_end,
                create_after=create_after,
                create_before=create_before,
                page=page,
                page_size=page_size,
            )
            results.extend(items)
            if len(results) >= total or not items:
                break
            if page == max_pages:
                logger.warning("pagination_tronquee", extra={"max_pages": max_pages, "total": total})
        return results
