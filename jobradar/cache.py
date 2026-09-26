import logging
from typing import Optional, Dict, Any
from jobradar.db import get_db

logger = logging.getLogger(__name__)

def get_cached_llm_result(fingerprint: str) -> Optional[Dict[str, Any]]:
    """Pobiera zapisany wczesniej wynik oceny LLM dla danej oferty."""
    db = get_db()
    try:
        response = db.table("llm_cache").select("*").eq("job_fingerprint", fingerprint).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Blad odczytu z cache LLM: {e}")
        return None

def save_llm_result_to_cache(fingerprint: str, result: Dict[str, Any], model_used: str):
    """Zapisuje wynik oceny LLM do bazy, aby nie zuzywac tokenow przy kolejnym uruchomieniu."""
    db = get_db()
    try:
        db.table("llm_cache").upsert({
            "job_fingerprint": fingerprint,
            "result": result,
            "model_used": model_used
        }).execute()
    except Exception as e:
        logger.error(f"Blad zapisu do cache LLM: {e}")

if __name__ == "__main__":
    # Prosty test weryfikujacy poprawnosc operacji Zapis/Odczyt
    print("Testuje dzialanie llm_cache...")
    test_hash = "test_fingerprint_123"
    test_data = {"score": 95, "summary": "To jest testowy zapis oceny AI", "phone_signals": []}
    
    print("Zapisuje dane do cache w Supabase...")
    save_llm_result_to_cache(test_hash, test_data, "test-model-v1")
    
    print("Odczytuje dane z cache...")
    cached = get_cached_llm_result(test_hash)
    
    if cached:
        print("Sukces! Odczytano dane:")
        print(cached["result"])
    else:
        print("Nie udalo sie odczytac danych z cache.")