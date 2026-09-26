"""Scraper dla WeWorkRemotely — kanały RSS."""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# WWR publikuje kilka kanałów. Bierzemy dwa główne.
FEEDS = (
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
)


def _parse_pubdate(value: str) -> str:
    """
    Konwertuje RFC 822 ('Mon, 23 Sep 2026 21:40:19 +0000')
    na ISO 8601 ('2026-09-23T21:40:19+00:00').
    """
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError):
        return ""


def _split_title(raw: str) -> tuple[str, str]:
    """
    WWR zwraca tytuł jako 'Company: Position'.
    Rozdziela na (company, title).
    """
    if ":" in raw:
        company, _, position = raw.partition(":")
        return company.strip(), position.strip()
    return "", raw.strip()


def _parse_feed(url: str) -> list[dict[str, Any]]:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "JobRadar/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:  # noqa: BLE001
        logger.error("Błąd pobierania RSS z %s: %s", url, e)
        return []

    jobs: list[dict[str, Any]] = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        company, title = _split_title(raw_title)

        # WWR często podaje region w <region> lub <category>
        region = (item.findtext("region") or "").strip()
        if not region:
            # fallback: z <category> lub z tytułu
            category = (item.findtext("category") or "").strip()
            region = category

        # Salary z <salary> (rzadko), reszta w description
        salary_raw = (item.findtext("salary") or "").strip()
        salary_min, salary_max = None, None
        # WWR podaje czasem w formacie "USD 80000-120000" — próbujemy parsować
        if salary_raw and "-" in salary_raw:
            digits = "".join(c for c in salary_raw if c.isdigit() or c == "-").split("-")
            try:
                if len(digits) == 2:
                    salary_min = int(digits[0]) or None
                    salary_max = int(digits[1]) or None
            except ValueError:
                pass

        jobs.append({
            "source": "wwr",
            "id": (item.findtext("guid") or item.findtext("link") or "").strip(),
            "title": title,
            "company": company,
            "location": region,
            "url": (item.findtext("link") or "").strip(),
            "tags": [],  # RSS nie daje tagów w spójnej formie
            "description": item.findtext("description") or "",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "posted_at": _parse_pubdate(item.findtext("pubDate") or ""),
        })

    return jobs


def fetch_jobs() -> list[dict[str, Any]]:
    """
    Pobiera i unifikuje oferty z kanałów RSS WeWorkRemotely.

    Kontrakt pól (spójny z remoteok.py / remotive.py / jobicy.py):
      source, id, title, company, location, url, tags, description,
      salary_min, salary_max, posted_at
    """
    all_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for feed_url in FEEDS:
        feed_jobs = _parse_feed(feed_url)
        for job in feed_jobs:
            # Dedup w obrębie WWR (te same oferty mogą być w 2 kanałach)
            jid = job["id"]
            if jid and jid in seen_ids:
                continue
            seen_ids.add(jid)
            all_jobs.append(job)

    logger.info("WWR: pobrano %d ofert (po dedupie)", len(all_jobs))
    return all_jobs


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