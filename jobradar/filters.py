"""
Twarde filtry (Krok 3 pipeline'u z dokumentacji §7).

Reguły:
  - Wszystkie filtry działają wg zasady opt-in (§5.3):
    brak klucza w prefs → filtr ignorowany.
  - Oferta musi przejść WSZYSTKIE aktywne filtry, żeby wrócić True.
  - Brak danych w ofercie (np. location="") → traktowane jako "nie wiem",
    więc filtr NIE odrzuca (bezpieczne dla użytkownika).
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Heurystyki: role → słowa kluczowe (do filtra roles.selected)
# ─────────────────────────────────────────────────────────────────────────────

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai_model_trainer": ("ai", "llm", "prompt", "annotation", "training", "rlhf", "evaluator"),
    "rlhf_contributor": ("rlhf", "red team", "safety", "moderation", "alignment"),
    "audio_image_annotator": ("audio", "image", "video", "transcription", "annotation"),
    "search_relevance_evaluator": ("relevance", "rater", "search", "evaluation"),
    "async_chat_support": ("chat", "support", "zendesk", "freshdesk", "intercom", "help scout"),
    "content_moderator": ("moderator", "moderation", "community", "discord", "forum"),
    "ecommerce_ops": ("shopify", "amazon", "ecommerce", "e-commerce", "catalog", "products"),
    "data_verification": ("verification", "kyc", "aml", "ocr", "erp", "data entry"),
    "virtual_assistant": ("assistant", "virtual assistant", "va ", "calendar", "research"),
    "bookkeeping_ap_ar": ("bookkeeping", "ap/ar", "ap-ar", "accounting", "invoicing"),
    "live_ops_risk": ("risk", "fraud", "monitoring", "live ops", "operations"),
    "qa_localization": ("qa", "localization", "localisation", "testing", "tester"),
    "trust_safety_analyst": ("trust", "safety", "policy", "escalation"),
    "no_code_automation": ("no-code", "nocode", "make.com", "zapier", "n8n", "airtable"),
    "technical_writer": ("technical writer", "documentation", "docs", "api docs"),
    "python_scraper": ("python", "scraper", "scraping", "crawler", "data extraction"),
    "devops_sre_async": ("devops", "sre", "infrastructure", "kubernetes", "terraform", "aws"),
    "ux_writer": ("ux writer", "microcopy", "content design", "ux writing"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Heurystyki: słowa kluczowe do filtra No-Phone
# ─────────────────────────────────────────────────────────────────────────────

PHONE_SIGNALS: tuple[str, ...] = (
    # EN
    "phone", "call", "voice", "speaking", "dictation", "verbal", "inbound",
    "outbound", "hotline", "helpdesk phone", "call center", "callcentre",
    "telephone", "dialing", "cold call",
    # PL
    "słuchawk", "dykcj", "rozmow", "telefon", "infolini", "call center",
    "obsługa połączeń", "rozmowy telefoniczne",
)

SPYWARE_SIGNALS: tuple[str, ...] = (
    # EN
    "time doctor", "timedoctor", "hubstaff", "screenshot", "screen shot",
    "screen capture", "mouse tracking", "keystroke", "keylogging",
    "activity monitor", "screen recording", "productivity monitor",
    "webcam", "always-on camera",
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _flatten_tags(tags: Any) -> set[str]:
    """Spłaszcza tagi i normalizuje do lowercase (API zwracają różne formaty)."""
    result: set[str] = set()
    if not tags:
        return result
    if isinstance(tags, str):
        return {tags.lower().strip()}
    for item in tags:
        if isinstance(item, list):
            for sub in item:
                if isinstance(sub, str):
                    result.add(sub.lower().strip())
        elif isinstance(item, str):
            result.add(item.lower().strip())
    return result


def _job_text(job: dict[str, Any]) -> str:
    """Zwraca połączony tekst oferty (title + description), lowercase."""
    parts = [
        str(job.get("title", "")),
        str(job.get("description", "")),
    ]
    return " ".join(parts).lower()


def _contains_any(haystack: str, needles: tuple[str, ...]) -> list[str]:
    """Zwraca listę pasujących needles (do logów)."""
    return [n for n in needles if n in haystack]


# ─────────────────────────────────────────────────────────────────────────────
# Indywidualne filtry
# ─────────────────────────────────────────────────────────────────────────────

def _check_blocklist(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Odrzuca ofertę, jeśli firma lub słowo z blocklisty pasuje."""
    blocklist = prefs.get("blocklist") or {}
    companies = [c.lower() for c in (blocklist.get("companies") or [])]
    keywords = [k.lower() for k in (blocklist.get("keywords") or [])]

    if companies:
        comp = str(job.get("company", "")).lower()
        if any(c in comp for c in companies):
            return False

    if keywords:
        text = _job_text(job)
        if any(k in text for k in keywords):
            return False

    return True


def _check_allowlist(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Jeśli allowlist niepusta, oferta MUSI być z jednej z tych firm."""
    allow = prefs.get("allowlist") or {}
    companies = [c.lower() for c in (allow.get("companies") or [])]
    if not companies:
        return True

    comp = str(job.get("company", "")).lower()
    return any(c in comp for c in companies)


def _check_roles(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """
    Sprawdza, czy oferta pasuje do którejś z wybranych ról.

    Dopasowanie: szukamy słów kluczowych roli w tags/tytule/description.
    match_mode: "any" (domyślnie) lub "all".
    """
    roles_cfg = prefs.get("roles") or {}
    selected = roles_cfg.get("selected") or []
    custom_tags = [t.lower() for t in (roles_cfg.get("custom_tags") or [])]
    match_mode = roles_cfg.get("match_mode", "any")

    if not selected and not custom_tags:
        return True  # brak wyboru → filtr ignorowany

    # Zbierz wszystkie keywordy z wybranych ról + custom tags
    keywords_per_role: list[set[str]] = []
    for role in selected:
        kws = set(ROLE_KEYWORDS.get(role, ()))
        if kws:
            keywords_per_role.append(kws)
    for tag in custom_tags:
        keywords_per_role.append({tag})

    # Tekst do przeszukania: tags + title + description
    tags_text = " ".join(_flatten_tags(job.get("tags")))
    haystack = f"{tags_text} {_job_text(job)}"

    # Sprawdź dopasowanie per rola
    matches: list[bool] = []
    for kws in keywords_per_role:
        hit = any(kw in haystack for kw in kws)
        matches.append(hit)

    if match_mode == "all":
        return all(matches)
    return any(matches)  # "any"


def _check_strict_no_phone(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    if not prefs.get("strict_no_phone"):
        return True
    hits = _contains_any(_job_text(job), PHONE_SIGNALS)
    if hits:
        logger.debug("Odrzucono (No-Phone): %s — sygnały: %s", job.get("title"), hits)
        return False
    return True


def _check_async_no_spyware(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    if not prefs.get("async_first_no_spyware"):
        return True
    hits = _contains_any(_job_text(job), SPYWARE_SIGNALS)
    if hits:
        logger.debug("Odrzucono (Spyware): %s — sygnały: %s", job.get("title"), hits)
        return False
    return True


def _check_geo(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """
    Filtruje po lokalizacji.
    - remote_worldwide_only=True: dopuszcza puste location oraz te ze słowem
      "worldwide", "anywhere", "global", "remote". Odrzuca konkretne kraje/miasta.
    - excluded_regions: odrzuca jeśli location zawiera któryś region.
    """
    geo = prefs.get("geo") or {}
    location = str(job.get("location", "")).lower().strip()

    excluded = [r.lower() for r in (geo.get("excluded_regions") or [])]
    if excluded and location:
        if any(r in location for r in excluded):
            return False

    if geo.get("remote_worldwide_only"):
        # Puste location → nie wiemy, przepuszczamy
        if not location:
            return True
        # Jeśli w location jest "worldwide" / "anywhere" / "global" — OK
        worldwide_markers = ("worldwide", "anywhere", "global", "remote")
        if any(m in location for m in worldwide_markers):
            return True
        # W przeciwnym razie to konkretny region — odrzuć
        return False

    return True


def _check_salary(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """
    Filtr finansowy:
      - enabled=False → ignorowany
      - require_disclosed=True → oferta musi mieć salary_min LUB salary_max
      - min_annual_usd / min_hourly_usd → salary_min musi być >= próg
        (uproszczenie: traktujemy salary_min jako roczne USD)
    """
    sal = prefs.get("salary") or {}
    if not sal.get("enabled"):
        return True

    s_min = job.get("salary_min")
    s_max = job.get("salary_max")

    if sal.get("require_disclosed") and not (s_min or s_max):
        return False

    min_annual = sal.get("min_annual_usd")
    if min_annual and s_min and s_min < min_annual:
        return False

    return True


def _check_freshness(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """
    Odrzuca oferty starsze niż freshness_hours.
    Jeśli brak posted_at lub błąd parsowania → przepuszcza.
    """
    hours = prefs.get("freshness_hours")
    if not hours:
        return True

    posted_at = job.get("posted_at")
    if not posted_at:
        return True

    try:
        # Obsługa ISO 8601 z timezone: "2026-09-24T16:00:06+00:00"
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_hours <= hours
    except (ValueError, TypeError):
        # Błąd parsowania → nie blokujemy oferty
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Główna funkcja
# ─────────────────────────────────────────────────────────────────────────────

_FILTERS = (
    ("blocklist", _check_blocklist),
    ("allowlist", _check_allowlist),
    ("roles", _check_roles),
    ("strict_no_phone", _check_strict_no_phone),
    ("async_no_spyware", _check_async_no_spyware),
    ("geo", _check_geo),
    ("salary", _check_salary),
    ("freshness", _check_freshness),
)


def apply_filters(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """
    Zwraca True, jeśli oferta przechodzi WSZYSTKIE aktywne filtry.
    Filtry działają wg zasady opt-in (§5.3): brak klucza → ignorowany.
    """
    for name, fn in _FILTERS:
        if not fn(job, prefs):
            logger.debug("Oferta odrzucona przez filtr: %s", name)
            return False
    return True