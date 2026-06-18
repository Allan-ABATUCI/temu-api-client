"""
Utilitaires — Sérialisation JSON

Auteur  : Allan ABATUCI
Modifié : 2026-06-17
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

LOGS_BASE = Path("/home/stagiaires/scripts/temu/logs")


def _daily_responses_dir() -> Path:
    now = datetime.now()
    d = LOGS_BASE / f"{now.year}" / f"{now.month:02d}" / f"{now.day:02d}" / "responses"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_json(data: dict | list, filename: str) -> Path:
    """Sauvegarde la réponse API dans logs/{Y}/{m}/{d}/responses/.

    - Fichier individuel (pretty-print) pour debug
    - Ligne compacte dans responses.log pour Promtail
    """
    out_dir = _daily_responses_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = out_dir / f"{filename}_{timestamp}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "level": "INFO",
        "logger": "temu_api_client.responses",
        "service": "responses",
        "message": "api_response",
        "log_type": "response",
        "action": filename,
        "file": path.name,
    }
    log_path = out_dir / "responses.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())

    logger.debug("reponse_sauvegardee", extra={"path": str(path)})
    return path
