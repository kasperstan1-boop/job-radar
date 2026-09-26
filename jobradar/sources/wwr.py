import requests
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_jobs() -> List[Dict[str, Any]]:
    """Pobiera i unifikuje oferty z publicznego kanału RSS We Work Remotely."""
    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        unified_jobs = []
        for item in root.findall('./channel/item'):
            title_full = item.findtext('title', '')
            # WWR formatuje tytuły jako "Firma: Stanowisko"
            company = ""
            title = title_full
            if ":" in title_full:
                company, title = title_full.split(":", 1)
            
            unified_jobs.append({
                "source": "wwr",
                "id": item.findtext('guid', ''),
                "title": title.strip(),
                "company": company.strip(),
                "location": "Anywhere", # WWR zazwyczaj wrzuca tu oferty globalne
                "url": item.findtext('link', ''),
                "tags": [],
                "description": item.findtext('description', ''),
                "salary_min": None,
                "salary_max": None
            })
        return unified_jobs
    except Exception as e:
        logger.error(f"Blad pobierania z WWR: {e}")
        return []

if __name__ == "__main__":
    jobs = fetch_jobs()
    print(f"Pobrano {len(jobs)} ofert z WWR.")