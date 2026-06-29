"""
Temu Open Platform API — Client HTTP bas niveau

Responsabilités :
  - POST vers l'API Temu avec les paramètres signés
  - Retry avec exponential backoff sur 429 et 5xx
  - Levée d'exceptions typées
  - Sauvegarde optionnelle des réponses brutes pour débogage

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import logging
import time

import requests
import requests.exceptions

from ..core import config
from ..core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TemuAPIError,
)
from ..core.logging_config import ensure_logging
from ..utils import save_json
from .auth import build_signed_params

logger = logging.getLogger(__name__)


class TemuHTTPClient:
    """
    Client HTTP bas niveau. Instancié par TemuClient (façade) uniquement.
    Ne pas instancier directement dans le code appelant.
    """

    BACKOFF_BASE   = 2.0
    BACKOFF_FACTOR = 2.0

    _RETRYABLE_NETWORK = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
    )

    def __init__(
        self,
        save_responses: bool = False,
        max_retries: int = 5,
        timeout: int = config.DEFAULT_TIMEOUT,
    ) -> None:
        ensure_logging()
        self.save_responses = save_responses
        self.max_retries    = max_retries
        self.timeout        = timeout
        self._session       = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def call(self, action: str, params: dict | None = None) -> dict:
        """
        Appelle l'endpoint Temu identifié par action.
        Retourne le contenu de response['result'] ou lève une TemuAPIError.
        """
        signed = build_signed_params(action, params)
        url    = config.API_BASE_URL

        for attempt in range(self.max_retries + 1):
            try:
                t0 = time.time()
                resp = self._session.post(url, json=signed, timeout=self.timeout)
                duration_ms = (time.time() - t0) * 1000
            except self._RETRYABLE_NETWORK as exc:
                logger.warning("network_error", extra={
                    "log_type": "request", "method": "POST", "url": url,
                    "action": action, "error": str(exc),
                    "duration_ms": round((time.time() - t0) * 1000, 2),
                })
                if attempt >= self.max_retries:
                    raise NetworkError(f"Erreur réseau persistante : {exc}") from exc
                self._wait(attempt)
                continue

            logger.info("api_call", extra={
                "log_type": "request", "method": "POST", "url": url,
                "action": action, "status_code": resp.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_body": params,
                "response_body": resp.text[:2000],
            })

            if resp.status_code == 200:
                return self._parse_success(resp, action)

            # _handle_error lève toujours pour les erreurs non-retriables ;
            # retourne le délai d'attente (int) ou None pour les cas retriables.
            retry_after = self._handle_error(resp, action, attempt)
            self._wait(attempt, retry_after=retry_after)

        raise TemuAPIError(f"Échec après {self.max_retries} tentatives sur {action}")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "TemuHTTPClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ─────────────────────────────────────────────────────────
    # Privé
    # ─────────────────────────────────────────────────────────

    def _parse_success(self, resp: requests.Response, action: str) -> dict:
        try:
            body = resp.json()
        except ValueError as exc:
            raise TemuAPIError("Réponse JSON invalide") from exc

        if self.save_responses:
            save_json(body, action.replace("/", "_"))

        # Temu renvoie errorCode (camelCase) != 1000000 pour les erreurs métier
        success    = body.get("success", True)
        error_code = str(body.get("errorCode", body.get("error_code", "1000000")))
        if not success or error_code not in ("0", "1000000"):
            msg = body.get("errorMsg") or body.get("error_msg") or "Erreur inconnue"
            logger.error("api_error_metier", extra={
                "log_type": "request", "action": action,
                "error_code": error_code, "error_msg": msg,
                "response_body": body,
            })
            if error_code in ("40001", "40002", "40003"):
                raise AuthError(msg, status_code=200, error_code=error_code)
            raise TemuAPIError(msg, status_code=200, error_code=error_code)

        return body.get("result", body)

    def _handle_error(self, resp: requests.Response, action: str, attempt: int) -> int | None:
        """
        Lève une exception pour toute erreur non-retriable.
        Pour les erreurs retriables (429, 5xx), retourne le délai à attendre
        en secondes (int) ou None si aucun délai spécifique n'est demandé.
        """
        code = resp.status_code
        body = resp.text[:500]

        if code in (401, 403):
            raise AuthError(
                f"Authentification refusée ({code}) sur {action}",
                status_code=code, response_body=body,
            )
        if code == 404:
            raise NotFoundError(f"Ressource introuvable ({action})", status_code=404)
        if code == 429:
            retry_after_raw = int(resp.headers.get("Retry-After", 0))
            retry_after     = retry_after_raw if retry_after_raw > 0 else None
            if attempt >= self.max_retries:
                raise RateLimitError(
                    f"Rate limit dépassé sur {action}",
                    retry_after=retry_after, status_code=429, response_body=body,
                )
            logger.warning("rate_limit", extra={"action": action, "attempt": attempt + 1, "max_retries": self.max_retries})
            return retry_after
        if code >= 500:
            if attempt >= self.max_retries:
                raise ServerError(f"Erreur serveur ({code}) sur {action}", status_code=code, response_body=body)
            logger.warning("erreur_serveur", extra={"code": code, "action": action, "attempt": attempt + 1, "max_retries": self.max_retries})
            return None

        raise TemuAPIError(f"Réponse inattendue ({code}) sur {action}", status_code=code, response_body=body)

    def _wait(self, attempt: int, retry_after: int | None = None) -> None:
        exp_delay = min(self.BACKOFF_BASE * (self.BACKOFF_FACTOR ** attempt), config.MAX_BACKOFF_SECONDS)
        delay = max(exp_delay, float(retry_after or 0))
        logger.warning("retry", extra={"delay_s": round(delay, 1)})
        time.sleep(delay)
