import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_jobs() -> List[Dict[str, Any]]:
    """Pobiera i unifikuje oferty z publicznego API Jobicy."""
    url = "https://jobicy.com/api/v2/remote-jobs"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json().get("jobs", [])
        
        unified_jobs = []
        for item in data:
            # Jobicy podaje tagi w formie pojedynczych stringów, łączymy je
            tags = []
            if item.get("jobIndustry"): tags.append(item.get("jobIndustry"))
            if item.get("jobType"): tags.append(item.get("jobType"))
            
            unified_jobs.append({
                "source": "jobicy",
                "id": str(item.get("id", "")),
                "title": item.get("jobTitle", ""),
                "company": item.get("companyName", ""),
                "location": item.get("jobGeo", ""),
                "url": item.get("url", ""),
                "tags": tags,
                "description": item.get("jobDescription", ""),
                "salary_min": item.get("annualSalaryMin"),
                "salary_max": item.get("annualSalaryMax")
            })
        return unified_jobs
    except Exception as e:
        logger.error(f"Blad pobierania z Jobicy: {e}")
        return []

if __name__ == "__main__":
    jobs = fetch_jobs()
    print(f"Pobrano {len(jobs)} ofert z Jobicy.")