"""
Configuration des logs — même standard que facturation.

Structure : logs/{année}/{mois}/{jour}/{service}/{service}.log

Usage :
    from temu_api_client.core.logging_config import setup_logging
    setup_logging("mon_script")          # JSON vers stdout + fichier journalier
    setup_logging("mon_script", level="DEBUG")  # verbosité maximale
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

LOGS_BASE = Path("/home/stagiaires/scripts/temu/logs")

_configured = False

_STANDARD_LOG_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName", "asctime",
})

_SENSITIVE_KEYS = frozenset({
    "email", "email_address", "emailaddress",
    "phone", "phone_number", "phonenumber", "mobile", "telephone",
    "first_name", "last_name", "firstname", "lastname",
    "full_name", "fullname", "customer_name", "customername",
    "buyer_name", "buyername", "recipient", "contact_name", "contactname",
    "address", "address1", "address2", "street", "street_address", "streetaddress",
    "city", "zip", "zipcode", "postal_code", "postalcode",
    "shipping_address", "shippingaddress", "billing_address", "billingaddress",
    "delivery_address", "deliveryaddress",
    "password", "passwd", "token", "access_token", "accesstoken",
    "refresh_token", "refreshtoken", "secret", "api_key", "apikey",
    "authorization", "iban", "bic", "card_number", "cardnumber",
})


def _scrub(obj, _depth: int = 0):
    if _depth > 8:
        return obj
    if isinstance(obj, dict):
        return {
            k: "***" if k.lower().replace("-", "_") in _SENSITIVE_KEYS
               else _scrub(v, _depth + 1)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub(item, _depth + 1) for item in obj]
    if isinstance(obj, str) and len(obj) > 1 and obj[0] in ("{", "["):
        try:
            return _scrub(json.loads(obj), _depth + 1)
        except (json.JSONDecodeError, ValueError):
            pass
    return obj


class JsonFormatter(logging.Formatter):
    """Formate chaque log en une ligne JSON — compatible Loki/Grafana."""

    def __init__(self, service: str):
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds"),
            "level":     record.levelname,
            "logger":    record.name,
            "service":   self._service,
            "message":   record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in _STANDARD_LOG_ATTRS and not key.startswith("_"):
                entry[key] = val
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(_scrub(entry), ensure_ascii=False, default=str)


class _DailyDirectoryFileHandler(logging.Handler):
    """Bascule vers logs/{année}/{mois}/{jour}/{service}/ à minuit."""

    def __init__(self, service_name: str, encoding: str = "utf-8"):
        super().__init__()
        self._service_name = service_name
        self._encoding     = encoding
        self._date         = None
        self._handler      = None
        self._switch_if_needed()

    def _path_for(self, date) -> Path:
        log_dir = LOGS_BASE / f"{date.year}" / f"{date.month:02d}" / f"{date.day:02d}" / self._service_name
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            log_dir = Path("/tmp") / "temu_logs" / f"{date.year}" / f"{date.month:02d}" / f"{date.day:02d}" / self._service_name
            log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{self._service_name}.log"

    def _switch_if_needed(self) -> None:
        today = datetime.now().date()
        if today == self._date:
            return
        new_handler = logging.FileHandler(self._path_for(today), encoding=self._encoding)
        if self.formatter is not None:
            new_handler.setFormatter(self.formatter)
        old_handler, self._handler, self._date = self._handler, new_handler, today
        if old_handler is not None:
            old_handler.close()

    @property
    def baseFilename(self) -> str:
        return self._handler.baseFilename

    def setFormatter(self, fmt) -> None:
        super().setFormatter(fmt)
        if self._handler is not None:
            self._handler.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        self._switch_if_needed()
        self._handler.emit(record)
        self._handler.flush()
        os.fsync(self._handler.stream.fileno())

    def close(self) -> None:
        if self._handler is not None:
            self._handler.close()
        super().close()


def log_api_call(
    logger: logging.Logger,
    method: str,
    url: str,
    *,
    status_code: int = None,
    duration_ms: float = None,
    request_body=None,
    response_body=None,
    error: str = None,
) -> None:
    """Enregistre un appel API externe en JSON structuré (log_type='request')."""
    level = logging.ERROR if (error or (status_code and status_code >= 400)) else logging.INFO
    extra: dict = {"log_type": "request", "method": method, "url": url}
    if status_code is not None:
        extra["status_code"] = status_code
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    if request_body is not None:
        extra["request_body"] = (
            request_body if isinstance(request_body, (dict, list))
            else str(request_body)
        )
    if response_body is not None:
        extra["response_body"] = (
            response_body if isinstance(response_body, (dict, list))
            else str(response_body)
        )
    if error:
        extra["error"] = error
    logger.log(level, f"{method} {url} → {status_code or 'ERR'}", extra=extra)


def setup_logging(service_name: str) -> Path:
    """
    Configure le logging vers stdout + fichier journalier.
    Retourne le chemin du fichier log du jour courant.

    Structure : logs/{année}/{mois}/{jour}/{service_name}/{service_name}.log
    """
    global _configured

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level      = getattr(logging, level_name, logging.INFO)

    formatter      = JsonFormatter(service_name)
    file_handler   = _DailyDirectoryFileHandler(service_name)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.setLevel(level)

    _configured = True
    return Path(file_handler.baseFilename)


def ensure_logging() -> None:
    """Auto-configure si aucun script n'a appelé setup_logging."""
    if not _configured:
        setup_logging("temu_api_client")


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Alias de compatibilité — redirige vers setup_logging."""
    if level != "INFO":
        os.environ["LOG_LEVEL"] = level.upper()
    setup_logging("temu_api_client")
