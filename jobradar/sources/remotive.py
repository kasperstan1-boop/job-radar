import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_jobs() -> List[Dict[str, Any]]:
    """Pobiera i unifikuje oferty z publicznego API Remotive."""
    url = "https://remotive.com/api/remote-jobs"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json().get("jobs", [])
        
        unified_jobs = []
        for item in data:
            unified_jobs.append({
                "source": "remotive",
                "id": str(item.get("id", "")),
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("candidate_required_location", ""),
                "url": item.get("url", ""),
                "tags": item.get("tags", []),
                "description": item.get("description", ""),
                "salary_min": None,  # Remotive rzadko podaje w czystych liczbach
                "salary_max": None
            })
        return unified_jobs
    except Exception as e:
        logger.error(f"Blad pobierania z Remotive: {e}")
        return []

if __name__ == "__main__":
    jobs = fetch_jobs()
    print(f"Pobrano {len(jobs)} ofert z Remotive.")