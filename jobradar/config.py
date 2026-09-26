"""
Konfiguracja globalna Job Radar.

Zmienne środowiskowe wczytywane z .env (lokalnie) lub GitHub Secrets (produkcja).
Stałe globalne (role, modele Gemini, limity) trzymane tutaj — jedno źródło prawdy.
"""

import logging
from functools import lru_cache
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jobradar.config")


# ─────────────────────────────────────────────────────────────────────────────
# Settings (zmienne środowiskowe)
# ─────────────────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # Resend
    resend_api_key: str = ""
    notification_email: str = ""

    # Opcjonalne
    teams_webhook_url: str = ""
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton — czyta .env tylko raz, przy pierwszym wywołaniu."""
    return Settings()


# ─────────────────────────────────────────────────────────────────────────────
# Stałe globalne
# ─────────────────────────────────────────────────────────────────────────────

# 18 tagów ról z dokumentacji (§2, 6 filarów)
ROLES: Final[tuple[str, ...]] = (
    # Filar 1: AI i Dane
    "ai_model_trainer",
    "rlhf_contributor",
    "audio_image_annotator",
    "search_relevance_evaluator",
    # Filar 2: Operacje cyfrowe
    "async_chat_support",
    "content_moderator",
    "ecommerce_ops",
    "data_verification",
    "virtual_assistant",
    "bookkeeping_ap_ar",
    # Filar 3: Live Ops
    "live_ops_risk",
    "qa_localization",
    "trust_safety_analyst",
    # Filar 4: IT i treści
    "no_code_automation",
    "technical_writer",
    "python_scraper",
    "devops_sre_async",
    "ux_writer",
)

# Priorytet modeli Gemini (od najwyższego RPM na free tier)
GEMINI_MODEL_PRIORITY: Final[tuple[str, ...]] = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
)

# Źródła ofert
SOURCES: Final[tuple[str, ...]] = ("remoteok", "remotive", "jobicy", "wwr")

# Limity LLM (bezpieczna matematyka z dokumentacji §8.7)
MAX_LLM_CALLS_PER_RUN: Final[int] = 120
THROTTLE_SECONDS: Final[float] = 4.0  # dla 15 RPM

# HTTP
HTTP_TIMEOUT_SECONDS: Final[int] = 10
HTTP_RETRY_COUNT: Final[int] = 2

# Freshness domyślne (godziny)
DEFAULT_FRESHNESS_HOURS: Final[int] = 24


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_gemini_key(api_key: str | None = None) -> bool:
    """
    Waliduje klucz Gemini API funkcjonalnie — nie po formacie.
    Obsługuje zarówno 'AQ.Ab8RN...', jak i 'AIzaSy...'.
    """
    key = api_key or get_settings().gemini_api_key
    if not key:
        logger.error("GEMINI_API_KEY jest pusty")
        return False

    try:
        from google import genai  # noqa: PLC0415

        client = genai.Client(api_key=key.strip())
        list(client.models.list())
        logger.info("Klucz Gemini: OK (prefiks=%s, długość=%d)", key[:6], len(key))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Walidacja klucza Gemini nieudana: %s", e)
        return False


def redact_key(key: str) -> str:
    """Zwraca bezpieczną reprezentację klucza do logów."""
    if not key:
        return "(pusty)"
    return f"{key[:6]}...({len(key)} znaków)"


def setup_monitoring() -> None:
    """Inicjalizuje Sentry, jeśli SENTRY_DSN jest ustawione."""
    settings = get_settings()
    if not settings.sentry_dsn:
        logger.info("Monitoring Sentry: wyłączony (brak SENTRY_DSN)")
        return

    try:
        import sentry_sdk  # noqa: PLC0415

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
        )
        logger.info("Monitoring Sentry: włączony")
    except ImportError:
        logger.warning("Monitoring Sentry: brak pakietu sentry-sdk")


# ─────────────────────────────────────────────────────────────────────────────
# Test CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Test konfiguracji Job Radar...")
    s = get_settings()

    checks = [
        ("SUPABASE_URL", s.supabase_url),
        ("SUPABASE_SERVICE_KEY", s.supabase_service_key),
        ("GEMINI_API_KEY", s.gemini_api_key),
        ("RESEND_API_KEY", s.resend_api_key),
        ("NOTIFICATION_EMAIL", s.notification_email),
        ("TEAMS_WEBHOOK_URL (opcjonalne)", s.teams_webhook_url),
        ("SENTRY_DSN (opcjonalne)", s.sentry_dsn),
    ]

    for name, value in checks:
        status = "✅" if value else "⚠️ "
        shown = redact_key(value) if "KEY" in name else (value or "(brak)")
        logger.info("%s %-40s %s", status, name, shown)

    logger.info("Role: %d tagów", len(ROLES))
    logger.info("Modele Gemini: %d w priorytecie", len(GEMINI_MODEL_PRIORITY))
    logger.info("MAX_LLM_CALLS_PER_RUN: %d", MAX_LLM_CALLS_PER_RUN)

    setup_monitoring()