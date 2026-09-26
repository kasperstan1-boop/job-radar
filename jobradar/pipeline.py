import os
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from jobradar.sources import remoteok, remotive, jobicy, wwr
from jobradar.fingerprint import generate_fingerprint
from jobradar.db import get_db, is_job_seen, mark_job_seen
from jobradar.filters import apply_filters
from jobradar.llm import analyze_job
from jobradar.notifier import notify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_PREFS = {
    "allowed_locations": ["Worldwide", "Remote", "Anywhere", "Europe", "UK"],
    "excluded_tags": ["php", "wordpress"],
}

# Limity zabezpieczające (Punkt 8.7 planu)
MAX_LLM_CALLS_PER_RUN = 120
THROTTLE_SECONDS = 4

def run_circuit_breaker(source_name: str) -> bool:
    db = get_db()
    try:
        res = db.table("pipeline_runs").select("source_stats").order("started_at", desc=True).limit(3).execute()
        if len(res.data) < 3: return True
            
        fails = sum(1 for run in res.data if run.get("source_stats", {}).get(source_name) == "failed")
        if fails >= 3:
            logger.warning(f"CIRCUIT BREAKER: Źródło {source_name} padło 3x z rzędu. Pomijam.")
            return False
        return True
    except Exception:
        return True

def fetch_all_jobs() -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    sources_to_check = {
        "remoteok": remoteok.fetch_jobs,
        "remotive": remotive.fetch_jobs,
        "jobicy": jobicy.fetch_jobs,
        "wwr": wwr.fetch_jobs
    }
    
    all_jobs, source_stats = [], {}
    
    for name, fetch_func in sources_to_check.items():
        if not run_circuit_breaker(name):
            source_stats[name] = "circuit_open_skipped"
            continue
            
        try:
            logger.info(f"Pobieram z {name}...")
            jobs = fetch_func()
            all_jobs.extend(jobs)
            source_stats[name] = "success"
        except Exception as e:
            logger.error(f"Awaria źródła {name}: {e}")
            source_stats[name] = "failed"
            
    return all_jobs, source_stats

def run_pipeline():
    run_id = str(uuid.uuid4())
    logger.info(f"START PIPELINE | Run ID: {run_id}")
    
    db = get_db()
    try:
        db.table("pipeline_runs").insert({"run_id": run_id, "status": "running"}).execute()
    except Exception as e:
        logger.error(f"Błąd bazy (start): {e}")

    raw_jobs, source_stats = fetch_all_jobs()
    logger.info(f"Pobrano łącznie {len(raw_jobs)} ofert.")

    approved_jobs = []
    llm_calls_made = 0
    
    for job in raw_jobs:
        fingerprint = generate_fingerprint(job)
        
        if is_job_seen(fingerprint):
            continue
            
        if not apply_filters(job, DEFAULT_PREFS):
            mark_job_seen(fingerprint)
            continue
            
        if llm_calls_made >= MAX_LLM_CALLS_PER_RUN:
            logger.warning("Osiągnięto twardy limit wywołań Gemini (120). Przerywam pętlę.")
            break
            
        logger.info(f"Analiza AI dla: {job.get('title')} ({job.get('company')})")
        time.sleep(THROTTLE_SECONDS) # Obowiązkowe usypianie skryptu (Rate Limit)
        
        llm_result = analyze_job(job)
        llm_calls_made += 1
        
        if llm_result:
            final_job = {**job, **llm_result}
            if final_job.get("score", 0) > 0:
                approved_jobs.append(final_job)
                
        mark_job_seen(fingerprint)

    if approved_jobs:
        approved_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        logger.info(f"Wysyłam raport. Liczba zaaprobowanych ofert: {len(approved_jobs)}")
        notify(approved_jobs)
    else:
        logger.info("Brak nowych ofert do wysłania.")

    try:
        db.table("pipeline_runs").update({
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "source_stats": source_stats,
            "llm_calls": llm_calls_made
        }).eq("run_id", run_id).execute()
        logger.info("PIPELINE ZAKOŃCZONY POMYŚLNIE.")
    except Exception as e:
        logger.error(f"Błąd bazy (koniec): {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_pipeline()