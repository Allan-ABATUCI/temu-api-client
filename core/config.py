"""
Temu Open Platform API — Configuration

Lit les variables d'environnement depuis .env (via python-dotenv).
La validation explicite se fait via validate() — pas à l'import,
pour ne pas bloquer l'importation du package sans credentials.

Variables requises dans .env :
    TEMU_APP_KEY      — clé publique de l'application
    TEMU_APP_SECRET   — secret de signature (ne jamais committer)
    TEMU_ACCESS_TOKEN — token vendeur (portail Temu Open Platform)

Variables optionnelles :
    TEMU_API_BASE_URL  — override de l'URL de base (sandbox / tests)
    TEMU_SIGNING_ALGO  — md5 (défaut) ou hmac_sha256

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import os
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path.home() / ".env")
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Credentials
# ─────────────────────────────────────────────────────────────

APP_KEY      = os.getenv("TEMU_APP_KEY", "").strip()
APP_SECRET   = os.getenv("TEMU_APP_SECRET", "").strip()
ACCESS_TOKEN = os.getenv("TEMU_ACCESS_TOKEN", "").strip()

# ─────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────

API_BASE_URL        = os.getenv("TEMU_API_BASE_URL", "https://openapi.temu.com/v1").rstrip("/")
MAX_BACKOFF_SECONDS = 32
DEFAULT_TIMEOUT     = 15
SIGNING_ALGORITHM   = os.getenv("TEMU_SIGNING_ALGO", "md5").lower()

def validate() -> None:
    """Lève EnvironmentError si des variables obligatoires sont absentes."""
    missing = [k for k, v in {
        "TEMU_APP_KEY":      APP_KEY,
        "TEMU_APP_SECRET":   APP_SECRET,
        "TEMU_ACCESS_TOKEN": ACCESS_TOKEN,
    }.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {missing}\n"
            "Copiez .env.example en .env et renseignez les valeurs."
        )
    logger.debug("config validée")
