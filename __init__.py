"""
temu_api_client — Package Python pour l'API Temu Open Platform

Point d'entrée unique : instancier TemuClient.

    from temu_api_client import TemuClient

    with TemuClient() as client:
        orders = client.orders.list_all(status="1")

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

from .facade import TemuClient
from .core.logging_config import setup_logging, configure_logging
from .core.exceptions import (
    TemuAPIError,
    AuthError,
    RateLimitError,
    NotFoundError,
    ServerError,
    NetworkError,
)

__all__ = [
    "TemuClient",
    "setup_logging",
    "configure_logging",
    "TemuAPIError",
    "AuthError",
    "RateLimitError",
    "NotFoundError",
    "ServerError",
    "NetworkError",
]

__version__ = "0.1.0"
__author__  = "Allan ABATUCI"
