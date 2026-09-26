import hashlib
import re
from typing import Any, Dict

def normalize_text(text: str) -> str:
    """Czyszczenie tekstu: male litery, usuniecie znakow specjalnych i spacji."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_salary_bucket(job: Dict[str, Any]) -> str:
    """Tworzy prosty znacznik (bucket) dla widelek placowych."""
    s_min = job.get("salary_min")
    s_max = job.get("salary_max")
    
    if s_min and s_max:
        return f"{s_min}-{s_max}"
    elif s_min:
        return f"min-{s_min}"
    elif s_max:
        return f"max-{s_max}"
    return "unknown"

def generate_fingerprint(job: Dict[str, Any]) -> str:
    """
    Tworzy unikalny hash SHA-256 dla oferty wg specyfikacji v3.6 (Punkt 7.1).
    Klucz: firma|tytul|lokalizacja|zarobki
    """
    company = normalize_text(job.get("company", ""))
    title = normalize_text(job.get("title", ""))
    location_scope = normalize_text(job.get("location", ""))
    salary = normalize_text(get_salary_bucket(job))

    key = f"{company}|{title}|{location_scope}|{salary}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()