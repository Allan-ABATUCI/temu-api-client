"""
Temu Open Platform API — Compliance & Governance Repository

Workflow for fixing blocked products:
  1. list_products(statusList=[1,4]) → find products with missing compliance
  2. get_extra_template(catId, goodsId) → get required templates + refPid/vid values
  3. get_fill_list(complianceInfoType=3) → get manufacturer repIds
  4. get_fill_list(complianceInfoType=2) → get EU responsible person repIds
  5. edit(goodsId, ...) → submit compliance data

Endpoints used:
  bg.local.compliance.goods.list.query
    List products with compliance status per template/GPSR/certificate.

  bg.local.goods.compliance.extra.template.get
    Get governance attribute templates for a product.
    REQUIRES catId (leaf category). Returns refPid, vid options, controlType.

  bg.local.goods.compliance.info.fill.list.query
    Get manufacturers (complianceInfoType=3) and responsible persons (complianceInfoType=2).
    REQUIRES page, size, complianceInfoType.

  bg.local.goods.compliance.rules.get
    Get compliance rules (checkInfoList) — CE marking, WEEE, voltage symbols, etc.

  bg.local.goods.compliance.edit
    Submit compliance data. Supports extraTemplate, gpsrInfo, certificateInfo.
    NOTE: use this endpoint, NOT temu.local.goods.compliance.v2.edit (v2 silently fails).

Compliance status values:
  1=Not submitted, 2=To be reviewed, 3=Reviewing,
  4=Action required, 5=Approved, 6=Rejected, 7=To be updated
"""

from __future__ import annotations

import logging
from ..http.client import TemuHTTPClient
from ..core.exceptions import ComplianceError

logger = logging.getLogger(__name__)


class ComplianceRepository:

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    # ── Query ────────────────────────────────────────────────

    def list_products(
        self,
        page: int = 1,
        page_size: int = 25,
        status_list: list[int] | None = None,
        search_text: str | None = None,
    ) -> dict:
        """List products with compliance status breakdown.

        Returns per product:
          extraTemplateInfoList: [{templateId, status}]
          gpsrInfoList: [{repType, status}]
          certificateInfoList: [{certType, status}]
        """
        params: dict = {"pageNo": page, "pageSize": page_size}
        if status_list:
            params["statusList"] = status_list
        if search_text:
            params["searchText"] = search_text
        return self._http.call("bg.local.compliance.goods.list.query", params)

    def get_extra_template(self, cat_id: int, goods_id: int) -> dict:
        """Get governance attribute templates for a product.

        Returns extraTemplateList with refPid, vid options, and controlType
        needed to fill each template via edit().

        Required templates have isRequired=True.
        Each template's templatePropertyDTOList contains:
          - refPid: attribute ID to use in edit()
          - controlType: 1=select(vid), 0/5=text(value), 17=multiline(inputValue)
          - propertyValueList: [{vid, valueName}] for select types
        """
        return self._http.call("bg.local.goods.compliance.extra.template.get", {
            "catId": cat_id,
            "goodsId": goods_id,
        })

    def get_fill_list(
        self,
        compliance_info_type: int,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """Get available manufacturers or responsible persons.

        Args:
            compliance_info_type: 2=EU responsible person, 3=manufacturer
            page: page number
            size: max 20 per page

        Returns authRepInfoList with repId to use in edit().
        repStatus: 3=Application successful (ready to use)
        """
        return self._http.call("bg.local.goods.compliance.info.fill.list.query", {
            "page": page,
            "size": size,
            "complianceInfoType": compliance_info_type,
        })

    def get_rules(self, goods_id: int) -> list[dict]:
        """Get compliance rules (checkInfoList) for a product.

        Returns checks like CE marking, WEEE label, voltage symbols.
        These are certificate requirements, not governance attributes.
        """
        result = self._http.call("bg.local.goods.compliance.rules.get", {
            "goodsId": goods_id,
        })
        return result.get("checkInfoList", [])

    # ── Edit ─────────────────────────────────────────────────

    def edit(
        self,
        goods_id: int,
        extra_template_detail_list: list[dict] | None = None,
        manufacturer_list: list[dict] | None = None,
        responsible_person_list: list[dict] | None = None,
    ) -> dict:
        """Submit compliance data for a product.

        Uses bg.local.goods.compliance.edit (NOT the v2 endpoint).

        Args:
            goods_id: Temu product ID
            extra_template_detail_list: governance templates, each with:
                For select attributes (controlType=1):
                  {"templateId": 305, "properties": {"<refPid>": [<vid>]}}
                For text/date attributes (controlType=0,5):
                  {"templateId": 1247, "inputText": {"<refPid>": {"name": "<value>"}}}
                For multiline text (controlType=17):
                  {"templateId": 51, "inputText": {"<refPid>": {"multiLineInputs": [{"name": "<text>"}]}}}
                For SKU-level templates (e.g. 1004 packaging):
                  {"templateId": 1004, "compliancePropertyList": [{
                      "specIdList": [<specId>],
                      "inputTextList": [{"properties": {...}, "inputText": {...}}]
                  }]}
            manufacturer_list: [{"repType": 3, "repId": <id>}]
            responsible_person_list: [{"repType": 2, "repId": <id>}]

        Raises:
            ComplianceError: if result.success is false
        """
        params: dict = {"goodsId": goods_id}

        if extra_template_detail_list:
            params["extraTemplate"] = {
                "extraTemplateDetailList": extra_template_detail_list,
            }

        if manufacturer_list or responsible_person_list:
            gpsr: dict = {}
            if manufacturer_list:
                gpsr["manufacturerList"] = manufacturer_list
            if responsible_person_list:
                gpsr["responsiblePersonList"] = responsible_person_list
            params["gpsrInfo"] = gpsr

        result = self._http.call("bg.local.goods.compliance.edit", params)

        if isinstance(result, dict) and result.get("success") is False:
            raise ComplianceError(
                f"Compliance edit failed for goodsId={goods_id}",
                error_code="COMPLIANCE_EDIT_FAILED",
            )

        return result
