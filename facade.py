"""
Temu Open Platform API — Façade principale (Facade Pattern)

TemuClient est le seul point d'entrée exposé aux utilisateurs du package.
Il câble ensemble le client HTTP et tous les repositories.

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from .core.logging_config import ensure_logging
from .http.client import TemuHTTPClient
from .resources.catalog   import CatalogRepository
from .resources.inventory import InventoryRepository
from .resources.orders    import OrderRepository
from .resources.shipping  import ShippingRepository


class TemuClient:
    """
    Façade unifiée pour l'API Temu Open Platform.

    Accès aux ressources via attributs :
      client.orders    → OrderRepository
      client.catalog   → CatalogRepository
      client.inventory → InventoryRepository
      client.shipping  → ShippingRepository

    Paramètres :
        save_responses  — sauvegarde les réponses JSON brutes dans ./responses/
        max_retries     — tentatives max sur erreurs réseau / 429 / 5xx
        timeout         — timeout HTTP en secondes
    """

    def __init__(
        self,
        save_responses: bool = False,
        max_retries: int = 5,
        timeout: int = 15,
    ) -> None:
        ensure_logging()
        self._http = TemuHTTPClient(
            save_responses=save_responses,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.orders    = OrderRepository(self._http)
        self.catalog   = CatalogRepository(self._http)
        self.inventory = InventoryRepository(self._http)
        self.shipping  = ShippingRepository(self._http)

    def close(self) -> None:
        """Libère la session HTTP. Appelé automatiquement avec le context manager."""
        self._http.close()

    def __enter__(self) -> "TemuClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
