"""
Główny pipeline Job Radar.

Kolejność (zgodnie z dokumentacją §7):
  1. Fetch z 4 źródeł
  2. Dedup między-źródłowy (fingerprint)
  3. Dedup per-user (seen_jobs)
  4. Twarde filtry (filters.py)
  5. Analiza LLM (llm.py)
  6. Generowanie + wysyłka digestu (notifier.py)
  7. Zapis metadanych (pipeline_runs, llm_cache)
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from jobradar.config import (
    MAX_LLM_CALLS_PER_RUN,
    SOURCES,
    THROTTLE_SECONDS,
    get_settings,
)
from jobradar.db import get_db, is_job_seen, mark_job_seen
from jobradar.filters import apply_filters
from jobradar.fingerprint import generate_fingerprint
from jobradar.llm import analyze_job
from jobradar.notifier import notify
from jobradar.sources import jobicy, remoteok, remotive, wwr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jobradar.pipeline")


SOURCE_FETCHERS = {
    "remoteok": remoteok.fetch_jobs,
    "remotive": remotive.fetch_jobs,
    "jobicy":   jobicy.fetch_jobs,
    "wwr":      wwr.fetch_jobs,
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Użytkownik (MVP: single-user)
# ─────────────────────────────────────────────────────────────────────────────

def get_active_user(db) -> dict | None:
    """Pobiera pierwszego aktywnego użytkownika z user_profiles."""
    try:
        res = (
            db.table("user_profiles")
            .select("id, email, config_token_hash, preferences")
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        if not res.data:
            logger.error("Brak aktywnego użytkownika w user_profiles.")
            return None
        return res.data[0]
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd wczytywania użytkownika: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Circuit breaker per źródło
# ─────────────────────────────────────────────────────────────────────────────

def is_source_healthy(db, source_name: str) -> bool:
    """Zwraca False, jeśli źródło padło 3× z rzędu (ostatnie 3 runy)."""
    try:
        res = (
            db.table("pipeline_runs")
            .select("source_stats")
            .order("started_at", desc=True)
            .limit(3)
            .execute()
        )
        if len(res.data) < 3:
            return True

        fails = sum(
            1 for run in res.data
            if (run.get("source_stats") or {}).get(source_name) == "failed"
        )
        if fails >= 3:
            logger.warning(
                "CIRCUIT BREAKER: źródło %s padło 3× z rzędu. Pomijam.",
                source_name,
            )
            return False
        return True
    except Exception:  # noqa: BLE001
        return True  # brak danych → zakładamy zdrowe


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fetch wszystkich źródeł
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_jobs(db) -> tuple[list[dict], dict[str, str]]:
    """Pobiera oferty z 4 źródeł. Nie przerywa całego pipeline przy 1 awarii."""
    all_jobs: list[dict] = []
    source_stats: dict[str, str] = {}

    for name in SOURCES:
        fetcher = SOURCE_FETCHERS.get(name)
        if not fetcher:
            logger.warning("Nieznane źródło: %s", name)
            source_stats[name] = "unknown_source"
            continue

        if not is_source_healthy(db, name):
            source_stats[name] = "circuit_open_skipped"
            continue

        try:
            logger.info("Pobieram z %s...", name)
            jobs = fetcher()
            all_jobs.extend(jobs)
            source_stats[name] = "success"
            logger.info("  %s: %d ofert", name, len(jobs))
        except Exception as e:  # noqa: BLE001
            logger.error("Awaria źródła %s: %s", name, e)
            source_stats[name] = "failed"

    logger.info("Łącznie pobrano %d ofert (przed dedupem).", len(all_jobs))
    return all_jobs, source_stats


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dedup między-źródłowy
# ─────────────────────────────────────────────────────────────────────────────

def dedup_between_sources(jobs: list[dict]) -> list[dict]:
    """Usuwa duplikaty między źródłami (ta sama firma + tytuł + lokalizacja)."""
    seen: set[str] = set()
    unique: list[dict] = []

    for job in jobs:
        fp = generate_fingerprint(job)
        if fp in seen:
            continue
        seen.add(fp)
        job["_fingerprint"] = fp  # zapisujemy dla kolejnych kroków
        unique.append(job)

    logger.info("Po dedupie między-źródłowym: %d unikalnych ofert.", len(unique))
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cache LLM
# ─────────────────────────────────────────────────────────────────────────────

def get_cached_llm(db, fingerprint: str) -> dict | None:
    try:
        res = (
            db.table("llm_cache")
            .select("result")
            .eq("job_fingerprint", fingerprint)
            .maybe_single()
            .execute()
        )
        return res.data.get("result") if res.data else None
    except Exception:
        return None


def save_llm_cache(db, fingerprint: str, result: dict, model: str) -> None:
    try:
        db.table("llm_cache").upsert({
            "job_fingerprint": fingerprint,
            "result": result,
            "model_used": model,
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("Nie zapisano llm_cache: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Główna pętla
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("═" * 60)
    logger.info("START PIPELINE | Run ID: %s", run_id)
    logger.info("═" * 60)

    db = get_db()

    # ── 6.1. Zapis startu ──
    try:
        db.table("pipeline_runs").insert({
            "run_id": run_id,
            "started_at": started_at,
            "status": "running",
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd zapisu pipeline_runs (start): %s", e)

    # ── 6.2. Wczytaj użytkownika ──
    user = get_active_user(db)
    if not user:
        _finalize_run(db, run_id, "failed", {}, 0, error="Brak aktywnego użytkownika.")
        return

    user_token_hash = user["config_token_hash"]
    user_email = user["email"]
    user_prefs = user.get("preferences") or {}

    logger.info("Użytkownik: %s (token=%s...)", user_email, user_token_hash[:12])

    # ── 6.3. Fetch ──
    raw_jobs, source_stats = fetch_all_jobs(db)

    # ── 6.4. Dedup między-źródłowy ──
    unique_jobs = dedup_between_sources(raw_jobs)

    # ── 6.5. Pętla: seen_jobs → filters → LLM ──
    approved: list[dict] = []
    llm_calls = 0
    skipped_seen = 0
    skipped_filters = 0
    skipped_limit = 0

    for job in unique_jobs:
        fingerprint = job["_fingerprint"]
        clean_job = {k: v for k, v in job.items() if not k.startswith("_")}

        # ── Seen jobs (per-user) ──
        if is_job_seen(fingerprint, user_token_hash):
            skipped_seen += 1
            continue

        # ── Twarde filtry ──
        if not apply_filters(clean_job, user_prefs):
            mark_job_seen(fingerprint, user_token_hash)
            skipped_filters += 1
            continue

        # ── Twardy limit LLM ──
        if llm_calls >= MAX_LLM_CALLS_PER_RUN:
            skipped_limit += 1
            continue

        # ── Cache LLM ──
        cached = get_cached_llm(db, fingerprint)
        if cached:
            logger.info("CACHE | %s", clean_job.get("title", "")[:60])
            llm_data = cached
            model_used = "cache"
        else:
            logger.info(
                "LLM  | %s @ %s",
                clean_job.get("title", "")[:50],
                clean_job.get("company", "")[:30],
            )
            time.sleep(THROTTLE_SECONDS)

            try:
                raw = analyze_job(clean_job)
                llm_data = raw.get("result", {})
                model_used = raw.get("model", "unknown")
                save_llm_cache(db, fingerprint, llm_data, model_used)
            except Exception as e:  # noqa: BLE001
                logger.error("LLM błąd dla %s: %s", clean_job.get("title", "?")[:40], e)
                mark_job_seen(fingerprint, user_token_hash)
                continue

            llm_calls += 1

        # ── Scal ofertę z wynikiem LLM ──
        final_job = {**clean_job, **llm_data}

        # ── Zapisz do seen_jobs (niezależnie od score) ──
        mark_job_seen(fingerprint, user_token_hash)

        # ── Filtruj słabe ──
        if final_job.get("score", 0) >= 50:
            approved.append(final_job)

    logger.info(
        "Podsumowanie: seen=%d, filters=%d, limit=%d, llm=%d, approved=%d",
        skipped_seen, skipped_filters, skipped_limit, llm_calls, len(approved),
    )

    # ── 6.6. Sortuj i ogranicz do max_jobs_per_digest ──
    approved.sort(key=lambda x: x.get("score", 0), reverse=True)
    max_jobs = (user_prefs.get("notifications") or {}).get("max_jobs_per_digest", 25)
    to_send = approved[:max_jobs]

    # ── 6.7. Wysyłka ──
    if to_send:
        logger.info("Wysyłam %d ofert (z %d zaakceptowanych).", len(to_send), len(approved))
        notify_result = notify(to_send, to_email=user_email)
        logger.info("Wynik wysyłki: %s", notify_result)
    else:
        logger.info("Brak nowych ofert do wysłania.")

    # ── 6.8. Finalizacja runu ──
    _finalize_run(
        db, run_id, "completed", source_stats, llm_calls,
        extra={"approved": len(approved), "sent": len(to_send)},
    )

    logger.info("═" * 60)
    logger.info("PIPELINE ZAKOŃCZONY.")
    logger.info("═" * 60)


def _finalize_run(
    db,
    run_id: str,
    status: str,
    source_stats: dict,
    llm_calls: int,
    extra: dict | None = None,
    error: str | None = None,
) -> None:
    """Zapisuje zakończenie runu do pipeline_runs."""
    payload = {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_stats": source_stats,
        "llm_calls": llm_calls,
    }
    if extra:
        payload["source_stats"] = {**source_stats, "_summary": extra}
    if error:
        payload["error"] = error

    try:
        db.table("pipeline_runs").update(payload).eq("run_id", run_id).execute()
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd finalizacji pipeline_runs: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_pipeline()