"""Generator HTML + plain text dla digestu Job Radar."""

import bleach
from typing import List, Dict, Any


def sanitize_html(text: str) -> str:
    """Czyszczenie tekstu ze złośliwych tagów HTML i skryptów JS."""
    if not text:
        return ""
    allowed_tags = ["b", "i", "u", "strong", "em", "p", "br", "ul", "ol", "li"]
    return bleach.clean(str(text), tags=allowed_tags, strip=True)


def _render_job_card(job: dict) -> str:
    score = job.get("score", 0)
    score_class = "score-high" if score >= 80 else "score-med" if score >= 50 else "score-low"

    safe_title = sanitize_html(job.get("title", "Brak tytułu"))
    safe_company = sanitize_html(job.get("company", "Nieznana firma"))
    safe_location = sanitize_html(job.get("location", "Zdalnie"))
    safe_salary = sanitize_html(job.get("salary_range") or "Brak widełek")
    safe_summary = sanitize_html(job.get("summary", ""))
    safe_url = sanitize_html(job.get("url", "#"))
    safe_source = sanitize_html(job.get("source", ""))

    flags = (job.get("red_flags") or []) + (job.get("spyware_signals") or []) + (job.get("phone_signals") or [])
    flags_html = ""
    if flags:
        safe_flags = [sanitize_html(f) for f in flags]
        flags_html = f'<div class="red-flags">⚠️ Uwaga: {", ".join(safe_flags)}</div>'

    source_html = f' | <em>{safe_source}</em>' if safe_source else ''

    return f"""
        <div class="job-card">
            <h3 class="job-title"><a href="{safe_url}" target="_blank" style="text-decoration: none; color: #0066cc;">{safe_title}</a></h3>
            <div class="job-company">{safe_company} | {safe_location}{source_html}</div>
            <div><span class="score {score_class}">Score: {score}%</span> <strong>{safe_salary}</strong></div>
            <div class="summary">{safe_summary}</div>
            {flags_html}
        </div>
    """


def generate_html_digest(jobs: list[dict]) -> str:
    if not jobs:
        return "<h2>Brak nowych ofert spełniających Twoje kryteria.</h2>"

    header = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .header { text-align: center; border-bottom: 2px solid #0066cc; padding-bottom: 10px; margin-bottom: 20px; }
            .job-card { border: 1px solid #ddd; border-radius: 6px; padding: 15px; margin-bottom: 15px; background: #fafafa; }
            .job-title { font-size: 18px; font-weight: bold; color: #0066cc; margin: 0 0 5px 0; }
            .job-company { font-size: 14px; color: #555; margin-bottom: 10px; }
            .score { display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: bold; color: #fff; }
            .score-high { background-color: #28a745; }
            .score-med { background-color: #ffc107; color: #333; }
            .score-low { background-color: #dc3545; }
            .summary { font-size: 14px; margin-top: 10px; line-height: 1.4; }
            .red-flags { color: #dc3545; font-size: 13px; margin-top: 10px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Job Radar - Twój codzienny raport</h2>
                <p>Znaleźliśmy dopasowane oferty pracy zdalnej</p>
            </div>
    """

    cards = "".join(_render_job_card(j) for j in jobs)

    footer = """
            <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #777;">
                <p>Wygenerowane przez Job Radar AI.</p>
                <p><a href="https://kasperstan1-boop.github.io/job-radar/">Zarządzaj preferencjami</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    return header + cards + footer


def generate_plain_text_digest(jobs: list[dict]) -> str:
    """Fallback plain text — dla klientów bez HTML."""
    if not jobs:
        return "Brak nowych ofert spełniających Twoje kryteria."

    lines = ["JOB RADAR - Twój codzienny raport", "=" * 40, ""]
    for j in jobs:
        source_str = f" [{j.get('source')}]" if j.get('source') else ""
        lines.append(f"[{j.get('score', 0)}%] {j.get('title', 'Brak')} @ {j.get('company', 'Brak')}{source_str}")
        lines.append(f"  {j.get('location', 'Zdalnie')} | {j.get('salary_range') or 'Brak widełek'}")
        lines.append(f"  {j.get('url', '')}")
        lines.append(f"  {j.get('summary', '')}")
        
        flags = (j.get("red_flags") or []) + (j.get("spyware_signals") or []) + (j.get("phone_signals") or [])
        if flags:
            lines.append(f"  ⚠️ Uwaga: {', '.join(flags)}")
            
        lines.append("")
        
    lines.append("Zarządzaj preferencjami: https://kasperstan1-boop.github.io/job-radar/")
    return "\n".join(lines)


if __name__ == "__main__":
    test_jobs = [
        {
            "title": "Senior Python Developer <script>alert('XSS')</script>",
            "company": "Acme Corp",
            "location": "Worldwide",
            "source": "remoteok",
            "url": "https://example.com",
            "score": 95,
            "salary_range": "$120k - $150k",
            "summary": "Praca asynchroniczna. <b>Pogrubienie</b>, ale skrypt zostanie usunięty.",
            "red_flags": ["Podejrzany proces rekrutacyjny"],
            "spyware_signals": [],
            "phone_signals": [],
        }
    ]

    html_out = generate_html_digest(test_jobs)
    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html_out)
    print("HTML: preview.html")
    print("\n--- Plain text ---")
    print(generate_plain_text_digest(test_jobs))