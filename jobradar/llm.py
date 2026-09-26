"""
Analiza oferty przez Gemini API.

Kontrakt:
    analyze_job(job: dict | str) -> {"result": {...}, "model": "gemini-..."}
"""

import json
import logging
import time

from google import genai
from google.genai import types

from jobradar.config import (
    GEMINI_MODEL_PRIORITY,
    get_settings,
    redact_key,
    validate_gemini_key,
)
from jobradar.prompt import get_prompt, get_system_instruction, response_schema

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Wybór modelu
# ─────────────────────────────────────────────────────────────────────────────

def _strip_prefix(name: str) -> str:
    """'models/gemini-3.1-flash-lite' -> 'gemini-3.1-flash-lite'"""
    return name.replace("models/", "", 1)


def get_models_to_try(client: genai.Client) -> list[str]:
    """
    Zwraca listę modeli do wypróbowania (bez prefiksu 'models/'), w kolejności priorytetu.
    """
    try:
        available = {
            _strip_prefix(m.name)
            for m in client.models.list()
            if m.supported_actions and "generateContent" in m.supported_actions
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd pobierania listy modeli: %s", e)
        return [_strip_prefix(m) for m in GEMINI_MODEL_PRIORITY[:2]]

    priority = [_strip_prefix(m) for m in GEMINI_MODEL_PRIORITY]
    models_to_try = [m for m in priority if m in available]

    if not models_to_try and available:
        fallback = sorted(available)[0]
        logger.warning(
            "Żaden model z priorytetu nie jest dostępny. Fallback: %s", fallback
        )
        models_to_try = [fallback]

    return models_to_try


# ─────────────────────────────────────────────────────────────────────────────
# Główna funkcja
# ─────────────────────────────────────────────────────────────────────────────

def analyze_job(job: dict | str) -> dict:
    """
    Analizuje ofertę przez Gemini.

    Args:
        job: dict z polami 'title', 'company', 'description' ALBO str (sam tekst).

    Returns:
        {"result": {...}, "model": "gemini-..."}

    Raises:
        ValueError: brak GEMINI_API_KEY
        RuntimeError: wszystkie modele zawiodły
    """
    # ── Normalizacja wejścia: str → dict ──
    if isinstance(job, str):
        job = {"title": "", "company": "", "description": job}

    # ── Klucz API z Settings (nie z os.environ!) ──
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()

    if not api_key:
        raise ValueError("Brak GEMINI_API_KEY w .env (Settings.gemini_api_key jest pusty).")

    if not validate_gemini_key(api_key):
        raise RuntimeError(
            f"Nieprawidłowy klucz Gemini: {redact_key(api_key)}. "
            "Sprawdź, czy klucz jest kompletny (AQ.Ab8... lub AIzaSy...)."
        )

    # ── Klient i modele ──
    client = genai.Client(api_key=api_key)
    models = get_models_to_try(client)

    if not models:
        raise RuntimeError("Brak dostępnych modeli Gemini obsługujących generateContent.")

    logger.debug("Modele do wypróbowania: %s", models)

    # ── Prompt ──
    prompt_text = get_prompt(
        job_title=job.get("title", "Brak tytułu"),
        company=job.get("company", "Brak firmy"),
        raw_text=job.get("description", ""),
    )

    config = types.GenerateContentConfig(
        system_instruction=get_system_instruction(),
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=0.0,
    )

    # ── Iteracja po modelach ──
    last_error: Exception | None = None

    for model_name in models:
        logger.info("Próbuję modelu: %s", model_name)

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=config,
            )

            # Preferuj wbudowany parser schematu
            parsed = getattr(response, "parsed", None)
            if parsed is not None:
                result = parsed if isinstance(parsed, dict) else parsed.model_dump()
            else:
                result = json.loads(response.text)

            return {"result": result, "model": model_name}

        except json.JSONDecodeError as e:
            logger.error("Model %s zwrócił niepoprawny JSON: %s", model_name, e)
            last_error = e
            continue

        except Exception as e:  # noqa: BLE001
            msg = str(e).lower()

            # Rate limit — przełącz model natychmiast
            if "429" in msg or "resource_exhausted" in msg:
                logger.warning("Limit modelu %s wyczerpany (429). Przełączam.", model_name)
                last_error = e
                continue

            # Błędy serwera 5xx — exponential backoff ×3
            if any(code in msg for code in ("500", "502", "503", "504", "unavailable")):
                logger.warning("Model %s zwrócił błąd serwera. Retry z backoffem.", model_name)
                for attempt in range(3):
                    time.sleep(2 ** attempt)
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt_text,
                            config=config,
                        )
                        parsed = getattr(response, "parsed", None)
                        if parsed is not None:
                            result = parsed if isinstance(parsed, dict) else parsed.model_dump()
                        else:
                            result = json.loads(response.text)
                        return {"result": result, "model": model_name}
                    except Exception as inner:  # noqa: BLE001
                        logger.warning("Retry %d/3 nieudany: %s", attempt + 1, inner)
                last_error = e
                continue

            logger.error("Błąd modelu %s: %s", model_name, e)
            last_error = e
            continue

    raise RuntimeError(
        f"Nie udało się przeanalizować oferty. Ostatni błąd: {last_error}"
    )