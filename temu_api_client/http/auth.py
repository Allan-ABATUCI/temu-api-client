"""
Temu Open Platform API — Signature des requêtes (Strategy Pattern)

Temu signe chaque requête en :
  1. Triant les paramètres par clé (ordre alphabétique)
  2. Concaténant : app_secret + (key+value)* + app_secret
  3. Appliquant MD5 ou HMAC-SHA256 selon la configuration
  4. Mettant le hash en majuscules

NOTE : vérifier la méthode exacte lors de l'obtention des credentials.

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
import logging

from ..core import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Strategy — interface
# ─────────────────────────────────────────────────────────────

class SigningStrategy(ABC):
    """Interface du pattern Strategy pour la signature de requêtes."""

    @abstractmethod
    def sign(self, params: dict[str, str], secret: str) -> str:
        """Retourne la signature hexadécimale en majuscules."""


# ─────────────────────────────────────────────────────────────
# Implémentations concrètes
# ─────────────────────────────────────────────────────────────

class MD5Signer(SigningStrategy):
    """Signature MD5 : secret + sorted(key+value) + secret → MD5 → UPPER."""

    def sign(self, params: dict[str, str], secret: str) -> str:
        payload = secret
        for key in sorted(params):
            payload += key + str(params[key])
        payload += secret
        return hashlib.md5(payload.encode("utf-8")).hexdigest().upper()


class HMacSHA256Signer(SigningStrategy):
    """Signature HMAC-SHA256 : sorted(key=value&) signé avec secret → UPPER."""

    def sign(self, params: dict[str, str], secret: str) -> str:
        message = "&".join(f"{k}={params[k]}" for k in sorted(params))
        digest  = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest.upper()


# ─────────────────────────────────────────────────────────────
# Registre des stratégies
# ─────────────────────────────────────────────────────────────

_SIGNERS: dict[str, SigningStrategy] = {
    "md5":         MD5Signer(),
    "hmac_sha256": HMacSHA256Signer(),
}


def _get_signer() -> SigningStrategy:
    algo = config.SIGNING_ALGORITHM
    if algo not in _SIGNERS:
        raise ValueError(
            f"TEMU_SIGNING_ALGO='{algo}' non supporté. "
            f"Valeurs valides : {list(_SIGNERS)}"
        )
    return _SIGNERS[algo]


# ─────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────

def build_signed_params(action: str, extra_params: dict | None = None) -> dict[str, str]:
    """
    Construit le dictionnaire de paramètres communs signé.

    Paramètres injectés automatiquement : app_key, access_token, timestamp, sign.
    Les extra_params spécifiques à l'endpoint sont fusionnés avant signature.
    """
    config.validate()

    params: dict[str, str] = {
        "app_key":      config.APP_KEY,
        "access_token": config.ACCESS_TOKEN,
        "timestamp":    str(int(time.time())),
        "data_type":    "JSON",
        "type":         action,
    }

    if extra_params:
        for k, v in extra_params.items():
            # Les dicts/listes sont sérialisés en JSON string (requis par Temu pour la signature)
            params[k] = json.dumps(v, separators=(",", ":")) if isinstance(v, (dict, list)) else str(v)

    params["sign"] = _get_signer().sign(params, config.APP_SECRET)
    logger.debug("params_signes", extra={"action": action})
    return params
