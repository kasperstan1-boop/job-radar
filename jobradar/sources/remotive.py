"""Scraper dla Remotive.com — publiczne API JSON."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"


def fetch_jobs() -> list[dict[str, Any]]:
    """
    Pobiera i unifikuje oferty z Remotive API.

    Kontrakt pól (spójny z remoteok.py):
      source, id, title, company, location, url, tags, description,
      salary_min, salary_max, posted_at
    """
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd pobierania danych z Remotive: %s", e)
        return []

    jobs_raw = data.get("jobs", [])
    unified: list[dict[str, Any]] = []

    for item in jobs_raw:
        # Remotive zwraca widełki jako pojedynczy string w "salary".
        # Nie parsujemy ich (zbyt różne formaty) — zostawiamy None.
        # Zgodnie z dokumentacją §8.4, LLM oceni ofertę po opisie.
        unified.append({
            "source": "remotive",
            "id": str(item.get("id", "")),
            "title": str(item.get("title", "")).strip(),
            "company": str(item.get("company_name", "")).strip(),
            "location": str(item.get("candidate_required_location", "")).strip(),
            "url": item.get("url", ""),
            "tags": item.get("tags", []),
            "description": item.get("description", ""),
            "salary_min": None,  # Remotive nie daje osobnych pól
            "salary_max": None,
            "posted_at": item.get("publication_date", ""),  # ISO 8601
        })

    logger.info("Remotive: pobrano %d ofert", len(unified))
    return unified


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    jobs = fetch_jobs()
    print(f"\nPobrano {len(jobs)} ofert.\n")

    if jobs:
        sample = jobs[0]
        print("--- Przykładowa oferta ---")
        for k, v in sample.items():
            if k == "description":
                print(f"{k:14} {str(v)[:80]}...")
            else:
                print(f"{k:14} {v!r}")