"""
Temu Open Platform API — Repository Expédition

Actions référencées :
  bg.order.ship       — confirmer l'expédition
  bg.logistics.list   — liste des transporteurs

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import logging

from ..http.client import TemuHTTPClient
from ..models import ShipmentConfirmation

logger = logging.getLogger(__name__)


class ShippingRepository:
    """Gestion des expéditions via l'API Temu."""

    def __init__(self, http: TemuHTTPClient) -> None:
        self._http = http

    def confirm_shipment(
        self,
        order_id: str,
        tracking_number: str,
        carrier_code: str,
    ) -> ShipmentConfirmation:
        """
        Confirme l'expédition d'une commande.
        carrier_code : code transporteur Temu (récupérable via list_carriers).
        """
        data = self._http.call("bg.order.ship", {
            "order_sn":             order_id,
            "tracking_number":      tracking_number,
            "logistics_company_id": carrier_code,
        })
        confirmation = ShipmentConfirmation.from_api(order_id, data)
        if confirmation.success:
            logger.info("expedition_confirmee", extra={"commande": order_id, "tracking": tracking_number})
        else:
            logger.warning("expedition_echec", extra={"commande": order_id})
        return confirmation

    def list_carriers(self) -> list[dict]:
        """Retourne la liste des transporteurs disponibles sur Temu."""
        data = self._http.call("bg.logistics.list")
        return data.get("logistics_list", [])
