"""
Modèles de données — Commandes (Parent Order + Order Items)

Structure Temu :
  Parent Order (parentOrderSn) → 1..N Order Items (orderSn, chacun lié à un SKU)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


STATUS_LABELS = {
    1: "pending",
    2: "unshipped",
    3: "canceled",
    4: "shipped",
    5: "delivered",
    41: "partially_shipped",
    51: "partially_delivered",
}


def _ts_to_dt(ts) -> datetime | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts))


@dataclass
class SubOrder:
    order_sn: str
    goods_id: int
    sku_id: int | None
    quantity: int
    original_quantity: int
    canceled_qty: int
    goods_name: str
    original_goods_name: str
    order_status: int
    thumb_url: str = ""
    order_create_time: datetime | None = None
    order_shipping_time: datetime | None = None
    fulfillment_type: str = ""

    @classmethod
    def from_api(cls, data: dict) -> SubOrder:
        return cls(
            order_sn=data.get("orderSn", ""),
            goods_id=int(data.get("goodsId", 0)),
            sku_id=int(data["skuId"]) if data.get("skuId") else None,
            quantity=int(data.get("quantity", 0)),
            original_quantity=int(data.get("originalOrderQuantity", 0)),
            canceled_qty=int(data.get("canceledQuantityBeforeShipment", 0)),
            goods_name=data.get("goodsName", ""),
            original_goods_name=data.get("originalGoodsName", ""),
            order_status=int(data.get("orderStatus", 0)),
            thumb_url=data.get("thumbUrl", ""),
            order_create_time=_ts_to_dt(data.get("orderCreateTime")),
            order_shipping_time=_ts_to_dt(data.get("orderShippingTime")),
            fulfillment_type=data.get("fulfillmentType", ""),
        )

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.order_status, str(self.order_status))


@dataclass
class ParentOrder:
    parent_order_sn: str
    status: int
    order_time: datetime | None
    update_time: datetime | None
    expect_ship_latest_time: datetime | None
    region_id: int | None
    site_id: int | None
    payment_type: str
    shipping_method: int | None
    confirm_time: datetime | None
    items: list[SubOrder] = field(default_factory=list)

    @classmethod
    def from_api(cls, page_item: dict) -> ParentOrder:
        po = page_item.get("parentOrderMap", {})
        order_list = page_item.get("orderList", [])

        return cls(
            parent_order_sn=po.get("parentOrderSn", ""),
            status=int(po.get("parentOrderStatus", 0)),
            order_time=_ts_to_dt(po.get("parentOrderTime")),
            update_time=_ts_to_dt(po.get("updateTime")),
            expect_ship_latest_time=_ts_to_dt(po.get("expectShipLatestTime")),
            region_id=int(po["regionId"]) if po.get("regionId") else None,
            site_id=int(po["siteId"]) if po.get("siteId") else None,
            payment_type=po.get("orderPaymentType", ""),
            shipping_method=int(po["shippingMethod"]) if po.get("shippingMethod") else None,
            confirm_time=_ts_to_dt(po.get("parentConfirmTime")),
            items=[SubOrder.from_api(o) for o in order_list],
        )

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, str(self.status))
