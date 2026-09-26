import os
import bleach
from typing import List, Dict, Any

def sanitize_html(text: str) -> str:
    """Czyszczenie tekstu ze zlosliwych tagow HTML i skryptow JS."""
    if not text:
        return ""
    # Zezwalamy tylko na podstawowe tagi formatowania tekstu
    allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li']
    return bleach.clean(str(text), tags=allowed_tags, strip=True)

def generate_html_digest(jobs: List[Dict[str, Any]]) -> str:
    """Generuje bezpieczny raport HTML z przefiltrowanych i ocenionych ofert."""
    if not jobs:
        return "<h2>Brak nowych ofert spełniających Twoje kryteria.</h2>"
        
    html = """
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
    
    for job in jobs:
        score = job.get("score", 0)
        score_class = "score-high" if score >= 80 else "score-med" if score >= 50 else "score-low"
        
        # Bezpieczne czyszczenie każdego elementu, który pochodzi z zewnątrz
        safe_title = sanitize_html(job.get('title', 'Brak tytułu'))
        safe_company = sanitize_html(job.get('company', 'Nieznana firma'))
        safe_location = sanitize_html(job.get('location', 'Zdalnie'))
        safe_salary = sanitize_html(job.get('salary_range') or 'Brak widełek')
        safe_summary = sanitize_html(job.get('summary', ''))
        
        flags_html = ""
        red_flags = job.get("red_flags", [])
        spyware = job.get("spyware_signals", [])
        phones = job.get("phone_signals", [])
        
        all_flags = [sanitize_html(flag) for flag in (red_flags + spyware + phones)]
        if all_flags:
            flags_html = f'<div class="red-flags">⚠️ Uwaga: {", ".join(all_flags)}</div>'

        html += f"""
            <div class="job-card">
                <h3 class="job-title"><a href="{job.get('url', '#')}" target="_blank" style="text-decoration: none; color: #0066cc;">{safe_title}</a></h3>
                <div class="job-company">{safe_company} | {safe_location}</div>
                <div><span class="score {score_class}">Score: {score}%</span> <strong>{safe_salary}</strong></div>
                <div class="summary">{safe_summary}</div>
                {flags_html}
            </div>
        """
        
    html += """
            <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #777;">
                <p>Wygenerowane przez Job Radar AI.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    print("Generuje testowy raport HTML (z sanityzacja Bleach)...")
    
    # Oferta ze złośliwym skryptem JS, żeby sprawdzić czy Bleach działa
    test_jobs = [
        {
            "title": "Senior Python Developer <script>alert('XSS')</script>",
            "company": "Acme Corp",
            "location": "Worldwide",
            "url": "https://example.com",
            "score": 95,
            "salary_range": "$120k - $150k",
            "summary": "Praca asynchroniczna. <b>Ten tekst zostanie pogrubiony</b>, ale skrypt JS z tytułu zostanie usunięty.",
            "red_flags": [],
            "spyware_signals": [],
            "phone_signals": []
        }
    ]
    
    html_output = generate_html_digest(test_jobs)
    
    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html_output)
        
    print("Gotowe! Utworzono plik preview.html z bezpiecznym kodem.")