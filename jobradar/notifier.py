"""Wysyłka digestu: Resend (email) + Teams (Adaptive Card)."""

import logging
import time

import requests

from jobradar.config import get_settings
from jobradar.digest import generate_html_digest, generate_plain_text_digest

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Resend (REST API)
# ─────────────────────────────────────────────────────────────────────────────

def send_email_resend(jobs: list[dict], to_email: str | None = None) -> bool:
    """
    Wysyła e-mail przez Resend API.
    Zwraca True jeśli wysłano, False w przeciwnym razie.
    """
    settings = get_settings()
    api_key = (settings.resend_api_key or "").strip()
    if not api_key:
        logger.warning("Brak RESEND_API_KEY. Pomijam wysyłkę e-maila.")
        return False

    recipient = to_email or settings.notification_email
    if not recipient:
        logger.warning("Brak adresu odbiorcy (notification_email). Pomijam.")
        return False

    html_content = generate_html_digest(jobs)
    text_content = generate_plain_text_digest(jobs)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": "Job Radar <onboarding@resend.dev>",
        "to": [recipient],
        "subject": f"Job Radar - Twój raport ({len(jobs)} ofert)",
        "html": html_content,
        "text": text_content,
        "headers": {
            "List-Unsubscribe": "<mailto:unsubscribe@jobradar.local>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.resend.com/emails",
                json=payload,
                headers=headers,
                timeout=15,
            )
            if r.status_code >= 500:
                logger.warning("Resend %d (próba %d/3). Retry...", r.status_code, attempt + 1)
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            logger.info("E-mail wysłany do %s (%d ofert)", recipient, len(jobs))
            return True
        except requests.RequestException as e:
            logger.error("Błąd Resend (próba %d/3): %s", attempt + 1, e)
            time.sleep(2 ** attempt)

    logger.error("Resend: wszystkie próby nieudane.")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Teams (Adaptive Card)
# ─────────────────────────────────────────────────────────────────────────────

def send_teams_digest(jobs: list[dict]) -> bool:
    """Wysyła digest na Teams przez webhook (Adaptive Card)."""
    settings = get_settings()
    webhook_url = (settings.teams_webhook_url or "").strip()
    if not webhook_url:
        logger.info("Brak TEAMS_WEBHOOK_URL. Pomijam powiadomienie Teams.")
        return False

    facts = [
        {
            "title": f"{j.get('score', 0)}% | {j.get('company', 'Firma')}",
            "value": j.get("title", "Stanowisko"),
        }
        for j in jobs[:10]
    ]

    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "Job Radar Digest",
                     "weight": "Bolder", "size": "Medium"},
                    {"type": "TextBlock", "text": f"Nowe dopasowane oferty ({len(jobs)}):",
                     "wrap": True},
                    {"type": "FactSet", "facts": facts},
                ],
            },
        }],
    }

    # KRYTYCZNE: Teams Workflows wymaga jawnego Content-Type
    headers = {"Content-Type": "application/json"}

    try:
        r = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        logger.info("Teams: powiadomienie wysłane (%d ofert)", len(jobs))
        return True
    except requests.RequestException as e:
        logger.error("Teams: błąd webhooka: %s", e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Orkiestrator
# ─────────────────────────────────────────────────────────────────────────────

def notify(jobs: list[dict], to_email: str | None = None) -> dict[str, bool]:
    """
    Wysyła digest wszystkimi skonfigurowanymi kanałami.
    Zwraca dict: {"email": True/False, "teams": True/False}
    """
    if not jobs:
        logger.info("Brak ofert do wysłania.")
        return {"email": False, "teams": False}

    return {
        "email": send_email_resend(jobs, to_email=to_email),
        "teams": send_teams_digest(jobs),
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    test_jobs = [
        {"title": "Senior Python Engineer", "company": "Tech Corp",
         "score": 92, "url": "https://example.com",
         "summary": "Async, no phone, worldwide.", "location": "Worldwide",
         "salary_range": "$120k"},
        {"title": "AI Data Scientist", "company": "AI startup",
         "score": 85, "url": "https://example.com",
         "summary": "Async ML role.", "location": "Worldwide",
         "salary_range": "brak"},
    ]

    result = notify(test_jobs)
    print(f"\nWynik wysyłki: {result}")