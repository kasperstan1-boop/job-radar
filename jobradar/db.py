import logging
from supabase import create_client, Client
from jobradar.config import get_settings

logger = logging.getLogger(__name__)

def get_db() -> Client:
    """Inicjalizuje klienta Supabase uzywajac kluczy z .env"""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)

def is_job_seen(fingerprint: str, token_hash: str = "default_user") -> bool:
    """Sprawdza, czy oferta (fingerprint) byla juz obsluzona w bazie."""
    db = get_db()
    try:
        response = db.table("seen_jobs").select("job_fingerprint") \
            .eq("token_hash", token_hash) \
            .eq("job_fingerprint", fingerprint).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Blad sprawdzania bazy danych: {e}")
        return False

def mark_job_seen(fingerprint: str, token_hash: str = "default_user"):
    """Zapisuje oferte w bazie 'seen_jobs', by nie wyslac jej drugi raz."""
    db = get_db()
    try:
        db.table("seen_jobs").insert({
            "token_hash": token_hash,
            "job_fingerprint": fingerprint
        }).execute()
    except Exception as e:
        logger.error(f"Blad zapisu do bazy danych: {e}")

if __name__ == "__main__":
    print("Testuje polaczenie z Supabase...")
    db = get_db()
    try:
        res = db.table("seen_jobs").select("*").limit(1).execute()
        print("Polaczenie z baza dziala poprawnie!")
    except Exception as e:
        print("Blad polaczenia:", e)