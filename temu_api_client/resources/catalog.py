"""
Temu Open Platform API — Catalog Repository

WHY: Centralizes all product CRUD operations behind typed methods.
Scripts should use this instead of calling client.call() directly — it
documents which endpoints exist, what parameters they take, and what they return.

Endpoints:
  bg.local.goods.add              — create product (v2 format)
  bg.local.goods.partial.update   — update specific fields without replacing everything
  bg.local.goods.detail.query     — get full product detail (images, attributes, compliance)
  bg.local.goods.list.query       — paginated product list (by status)
  bg.local.goods.delete           — delete product
  temu.local.sku.list.retrieve    — paginated SKU list with pageToken (no page limit)
  temu.local.goods.image.v2.upload — upload image to Temu CDN
  bg.local.goods.sku.out.sn.check — check if SKU already exists
"""

from __future__ import annotations

import logging
from ..http.client import TemuHTTPClient

logger = logging.getLogger(__name__)


class CatalogRepository:
    """Product catalog operations via the Temu API."""

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    # ── Create ───────────────────────────────────────────────

    def create(self, payload: dict) -> dict:
        """Create a product via bg.local.goods.add (v2).

        Payload built by catalog.builders.payload.ProductPayloadBuilder.
        Returns dict with goodsId and skuInfoList.
        """
        return self._http.call("bg.local.goods.add", payload)

    # ── Read ─────────────────────────────────────────────────

    def get_detail(self, goods_id: int) -> dict:
        """Get full product detail including images, attributes, trademark, secondHand.

        Returns the raw API result dict. Does NOT return compliance status
        (use ComplianceRepository for that).
        """
        return self._http.call("bg.local.goods.detail.query", {
            "goodsId": goods_id,
            "versionQueryType": 1,
        })

    def list_by_status(
        self,
        status_type: int,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """List products by status via bg.local.goods.list.query.

        Args:
            status_type: 1=online, 3=sold_out, 4=not_published, 5=draft, 6=deleted
            page: page number (starts at 1)
            page_size: max 100

        Returns dict with goodsList and total.
        WHY not pageToken: this endpoint uses pageNo, not pageToken.
        For unlimited pagination, use list_skus() instead.
        """
        return self._http.call("bg.local.goods.list.query", {
            "pageNo": page,
            "pageSize": page_size,
            "goodsSearchType": status_type,
            "goodsStatusFilterType": status_type,
        })

    def list_skus(
        self,
        status: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> dict:
        """List SKUs via temu.local.sku.list.retrieve.

        Uses pageToken pagination — no page limit. Call repeatedly with the
        returned nextToken until it's None.

        Args:
            status: ACTIVE, INACTIVE, INCOMPLETE, or DRAFT
            page_size: max 100
            page_token: from previous response's pagination.nextToken
        """
        params: dict = {"skuSearchType": status, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._http.call("temu.local.sku.list.retrieve", params)

    def check_sku_exists(self, skus: list[str]) -> dict:
        """Check if SKUs already exist on Temu.

        Returns resultList with isDuplicate and duplicateGoodsId per SKU.
        WHY: bg.local.goods.add fails with "SKU duplicated" if the SKU exists.
        Check before creating to avoid wasting an API call.
        """
        return self._http.call("bg.local.goods.sku.out.sn.check", {
            "outSkuSnList": skus,
        })

    # ── Update ───────────────────────────────────────────────

    def partial_update(self, payload: dict) -> dict:
        """Update specific product fields via bg.local.goods.partial.update.

        payload must include goodsId. Other fields are optional:
          goodsBasic (catId, goodsName, goodsCarouselImage, detailImage)
          goodsTrademark (brandId, trademarkId)
          secondHand (secondHandGoods, level)
          goodsProperty (goodsProperties list of refPid/vid)
          goodsOriginInfo (agreeDefaultOriginRegion)
          certificationInfo (extraTemplate)
          skuList (price, images, dimensions — requires images when included)
          gpsrInfo (agreeDefaultOriginRegion)

        WHY partial: bg.local.goods.update validates ALL fields and often rejects.
        partial.update only validates the fields you send.

        GOTCHAS:
          - Always include secondHand when updating (Temu requires it)
          - goodsProperty triggers validation of ALL required attributes
          - skuList requires images + dimensions or fails with "Upload image URL link"
          - Product goes to "processing" after update — can't update again for ~30s
        """
        return self._http.call("bg.local.goods.partial.update", payload)

    # ── Delete ───────────────────────────────────────────────

    def delete(self, goods_id: int) -> dict:
        """Delete a product via temu.local.goods.delete."""
        return self._http.call("temu.local.goods.delete", {"goodsId": goods_id})

    # ── Images ───────────────────────────────────────────────

    def upload_image(self, file_url: str) -> str | None:
        """Upload an image to Temu CDN via temu.local.goods.image.v2.upload.

        Args:
            file_url: source image URL (any public URL)

        Returns CDN URL (img-eu.kwcdn.com) or None if upload failed.
        WHY: Temu requires images on their CDN. Source URLs from eBay/Cdiscount
        must be uploaded first. Takes ~2s per image.
        """
        try:
            result = self._http.call(
                "temu.local.goods.image.v2.upload",
                {"fileUrl": file_url, "usage": 1},
            )
            return (result.get("images") or [{}])[0].get("url") or result.get("imgUrl")
        except Exception:
            return None

    # ── Attributes ───────────────────────────────────────────

    def get_category_attributes(self, cat_id: int) -> dict:
        """Get product attribute template for a category.

        Returns attributeList with refPid, required flag, and valid vid values.
        WHY: Each category has different required attributes. Sending a refPid
        that doesn't exist in the template causes "Invalid attribute".
        """
        return self._http.call("temu.local.product.attributes.get", {
            "catId": cat_id,
        })
