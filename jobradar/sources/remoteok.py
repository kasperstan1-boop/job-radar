"""Scraper dla RemoteOK.com — publiczne API JSON."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"
USER_AGENT = "JobRadar/1.0 (Automated Job Board Aggregator)"


def fetch_jobs() -> list[dict[str, Any]]:
    """
    Pobiera i unifikuje oferty z publicznego API RemoteOK.

    Pola wynikowe (kontrakt spójny między źródłami):
      source, id, title, company, location, url, tags, description,
      salary_min, salary_max, posted_at
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd pobierania danych z RemoteOK: %s", e)
        return []

    unified: list[dict[str, Any]] = []
    # Pierwszy element to metadane API — pomijamy
    for item in data[1:]:
        salary_min = item.get("salary_min") or None
        salary_max = item.get("salary_max") or None

        unified.append({
            "source": "remoteok",
            "id": str(item.get("id", "")),
            "title": item.get("position", "").strip(),
            "company": item.get("company", "").strip(),
            "location": item.get("location", "").strip(),
            "url": item.get("url", ""),
            "tags": item.get("tags", []),
            "description": item.get("description", ""),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "posted_at": item.get("date", ""),  # ISO 8601
        })

    logger.info("RemoteOK: pobrano %d ofert", len(unified))
    return unified


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    jobs = fetch_jobs()
    print(f"\nPobrano {len(jobs)} ofert.\n")

    if jobs:
        sample = next((j for j in jobs if j["salary_min"]), jobs[0])
        print("--- Przykładowa oferta (z widełkami jeśli są) ---")
        for k, v in sample.items():
            if k == "description":
                print(f"{k:14} {str(v)[:80]}...")
            else:
                print(f"{k:14} {v!r}")