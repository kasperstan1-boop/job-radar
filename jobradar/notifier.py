import os
import logging
import requests
from typing import List, Dict, Any
from jobradar.digest import generate_html_digest

logger = logging.getLogger(__name__)

def send_email_resend(html_content: str):
    """Wysyła e-mail za pomocą Resend API (bez wymogu własnej domeny)."""
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not resend_api_key:
        logger.warning("Brak klucza RESEND_API_KEY w .env. Pomijam wysyłkę e-maila.")
        return

    # W darmowym Resend e-maile wychodzą od onboarding@resend.dev 
    # i mogą być dostarczone TYLKO na adres zweryfikowany w panelu Resend.
    to_email = os.environ.get("NOTIFICATION_EMAIL", "twoj_email@example.com")

    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": "onboarding@resend.dev",
        "to": to_email,
        "subject": "Job Radar - Twój codzienny raport (oferty asynchroniczne)",
        "html": html_content
    }

    try:
        response = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("E-mail wysłany pomyślnie przez Resend!")
    except Exception as e:
        logger.error(f"Błąd wysyłki e-mail przez Resend: {e}")

def send_teams_digest(jobs: List[Dict[str, Any]]):
    """Wysyła raport na kanał MS Teams w formacie Adaptive Card (wymagane przez Workflows)."""
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.info("Brak TEAMS_WEBHOOK_URL w .env. Pomijam powiadomienie Teams.")
        return

    facts = [
        {"title": f"{j.get('score', 0)}% | {j.get('company', 'Firma')}", "value": j.get('title', 'Stanowisko')}
        for j in jobs[:10]  # Wysyłamy max 10 ofert, żeby nie przeładować karty w Teams
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
                    {"type": "TextBlock", "text": "Job Radar Digest", "weight": "Bolder", "size": "Medium"},
                    {"type": "TextBlock", "text": "Nowe dopasowane oferty (No-Phone):", "wrap": True},
                    {"type": "FactSet", "facts": facts},
                ],
            },
        }],
    }

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("Powiadomienie Teams wysłane pomyślnie!")
    except Exception as e:
        logger.error(f"Błąd wysyłki webhooka na Teams: {e}")

def notify(jobs: List[Dict[str, Any]]):
    """Orkiestrator powiadomień - wysyła raport wszystkimi skonfigurowanymi kanałami."""
    if not jobs:
        logger.info("Brak ofert do wysłania.")
        return

    html_content = generate_html_digest(jobs)
    send_email_resend(html_content)
    send_teams_digest(jobs)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testuję moduł powiadomień...")
    
    test_jobs = [
        {"title": "Senior Python Backend Engineer", "company": "Tech Corp", "score": 92, "url": "http://example.com"},
        {"title": "AI Data Scientist", "company": "AI startup", "score": 85, "url": "http://example.com"}
    ]
    
    notify(test_jobs)
    print("Test zakończony. Sprawdź terminal pod kątem ewentualnych ostrzeżeń o braku kluczy.")