"""Scraper dla Jobicy.com — publiczne API JSON."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# count=50 → maks. na raz. geo=anywhere → oferty remote worldwide.
API_URL = "https://jobicy.com/api/v2/remote-jobs"
PARAMS = {"count": 50, "geo": "anywhere"}


def _parse_salary(value: Any) -> int | None:
    """Jobicy zwraca salary jako string lub int. Konwertujemy bezpiecznie."""
    if value is None:
        return None
    try:
        n = int(float(value))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def fetch_jobs() -> list[dict[str, Any]]:
    """
    Pobiera i unifikuje oferty z Jobicy API.

    Kontrakt pól (spójny z remoteok.py / remotive.py):
      source, id, title, company, location, url, tags, description,
      salary_min, salary_max, posted_at
    """
    try:
        response = requests.get(API_URL, params=PARAMS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd pobierania danych z Jobicy: %s", e)
        return []

    jobs_raw = data.get("jobs", [])
    unified: list[dict[str, Any]] = []

    for item in jobs_raw:
        # Jobicy ma: jobIndustry (lista), jobType (lista), jobLevel
        # Tagi budujemy z industry + type + level
        tags: list[str] = []
        for field in ("jobIndustry", "jobType", "jobLevel"):
            val = item.get(field)
            if isinstance(val, list):
                tags.extend([str(v).lower() for v in val])
            elif isinstance(val, str):
                tags.append(val.lower())

        unified.append({
            "source": "jobicy",
            "id": str(item.get("id", "")),
            "title": str(item.get("jobTitle", "")).strip(),
            "company": str(item.get("companyName", "")).strip(),
            "location": str(item.get("jobGeo", "")).strip(),
            "url": item.get("url", ""),
            "tags": tags,
            "description": item.get("jobDescription", "") or item.get("jobExcerpt", ""),
            "salary_min": _parse_salary(item.get("annualSalaryMin")),
            "salary_max": _parse_salary(item.get("annualSalaryMax")),
            "posted_at": item.get("pubDate", ""),  # ISO 8601
        })

    logger.info("Jobicy: pobrano %d ofert", len(unified))
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