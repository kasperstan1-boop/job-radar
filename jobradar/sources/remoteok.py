import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_jobs() -> List[Dict[str, Any]]:
    """Pobiera i unifikuje oferty z publicznego API RemoteOK."""
    url = "https://remoteok.com/api"
    
    # RemoteOK blokuje domyślne skrypty, więc musimy ustawić własny User-Agent
    headers = {
        "User-Agent": "JobRadar/1.0 (Automated Job Board Aggregator)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        unified_jobs = []
        # Pierwszy element w RemoteOK API to często metadane, oferty zaczynają się od indeksu 1
        for item in data[1:]:
            unified_jobs.append({
                "source": "remoteok",
                "id": str(item.get("id", "")),
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "tags": item.get("tags", []),
                "description": item.get("description", ""),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max")
            })
        return unified_jobs
    
    except Exception as e:
        logger.error(f"Blad pobierania danych z RemoteOK: {e}")
        return []

if __name__ == "__main__":
    # Szybki test - pobranie i wyświetlenie w konsoli pierwszej oferty
    print("Pobieram dane z RemoteOK...")
    jobs = fetch_jobs()
    print(f"Pobrano {len(jobs)} ofert.")
    
    if jobs:
        print("\n--- Przykladowa oferta ---")
        print(f"Firma:    {jobs[0]['company']}")
        print(f"Tytul:    {jobs[0]['title']}")
        print(f"Lokacja:  {jobs[0]['location']}")
        print(f"Tagi:     {jobs[0]['tags']}")
        print(f"Widełki:  {jobs[0]['salary_min']} - {jobs[0]['salary_max']}")
        print(f"URL:      {jobs[0]['url']}")