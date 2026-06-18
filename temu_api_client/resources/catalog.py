"""
Temu Open Platform API — Repository Catalogue

Actions référencées :
  bg.goods.list    — liste des produits
  bg.goods.detail  — détail d'un produit
  bg.goods.edit    — mise à jour d'un produit

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from __future__ import annotations

import logging

from ..core.exceptions import TemuAPIError
from ..http.client import TemuHTTPClient
from ..models import Product

logger = logging.getLogger(__name__)


class CatalogRepository:
    """Accès au catalogue produits via l'API Temu."""

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    def list(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Product], bool]:
        """Retourne (products, has_more)."""
        params: dict = {"page_no": page, "page_size": page_size}
        if status:
            params["goods_status"] = status

        data     = self._http.call("bg.goods.list", params)
        raw_list = data.get("goods_list", [])
        has_more = data.get("has_more", False)
        products = [Product.from_api(p) for p in raw_list]

        logger.debug("produits_recus", extra={"page": page, "count": len(products)})
        return products, has_more

    def get(self, product_id: str) -> Product:
        """Retourne le détail complet d'un produit."""
        data         = self._http.call("bg.goods.detail", {"goods_id": product_id})
        product_data = data.get("goods_info")
        if product_data is None:
            raise TemuAPIError(
                f"Champ 'goods_info' absent de la réponse pour le produit {product_id}",
                error_code="MISSING_FIELD",
            )
        return Product.from_api(product_data)

    def list_all(self, status: str | None = None, page_size: int = 50) -> list[Product]:
        """Itère sur toutes les pages et retourne la liste complète."""
        results: list[Product] = []
        page = 1
        while True:
            items, has_more = self.list(status=status, page=page, page_size=page_size)
            results.extend(items)
            if not has_more:
                break
            page += 1
        return results

    def update_price(self, product_id: str, sku: str, price: float) -> bool:
        """Met à jour le prix d'un SKU. Retourne True si succès."""
        data = self._http.call("bg.goods.edit", {
            "goods_id": product_id,
            "sku_id":   sku,
            "price":    str(price),
        })
        return bool(data.get("success", False))
