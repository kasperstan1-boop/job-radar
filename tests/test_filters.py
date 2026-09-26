"""Test modułu jobradar.filters — weryfikacja wszystkich filtrów."""
from jobradar.filters import apply_filters


def main():
    # ── Oferta A: idealna — no-phone, async, worldwide, Python ──
    job_a = {
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "location": "Worldwide",
        "description": "Async work via Slack and GitHub. No meetings. Build scrapers in Python.",
        "tags": ["python", "scraper", "async"],
        "salary_min": 80000,
        "salary_max": 120000,
        "posted_at": "2026-09-26T08:00:00+00:00",
    }
    # ── Oferta B: ma call center → odrzucona przez strict_no_phone ──
    job_b = {
        "title": "Customer Support Representative",
        "company": "Globex",
        "location": "Worldwide",
        "description": "Handle inbound calls with excellent dictation. 40h on the phone.",
        "tags": ["support"],
        "salary_min": 40000,
        "salary_max": 50000,
        "posted_at": "2026-09-26T08:00:00+00:00",
    }
    # ── Oferta C: ma spyware → odrzucona przez async_no_spyware ──
    job_c = {
        "title": "Data Entry Specialist",
        "company": "Initech",
        "location": "Worldwide",
        "description": "We use Time Doctor with screenshots every 10 minutes. Async work.",
        "tags": ["data-entry"],
        "salary_min": 30000,
        "salary_max": 40000,
        "posted_at": "2026-09-26T08:00:00+00:00",
    }
    # ── Oferta D: stara (10 dni) → odrzucona przez freshness ──
    job_d = {
        "title": "Python Scraper",
        "company": "OldCo",
        "location": "Worldwide",
        "description": "Async work.",
        "tags": ["python"],
        "salary_min": 70000,
        "salary_max": 90000,
        "posted_at": "2026-09-16T08:00:00+00:00",  # 10 dni temu
    }
    # ── Oferta E: konkretny region (US only) → odrzucona przez geo ──
    job_e = {
        "title": "Python Developer",
        "company": "USCo",
        "location": "US Only",
        "description": "Async work via Slack.",
        "tags": ["python"],
        "salary_min": 90000,
        "salary_max": 120000,
        "posted_at": "2026-09-26T08:00:00+00:00",
    }
    # ── Oferta F: PHP dev (nie pasuje do wybranych ról) → odrzucona przez roles ──
    job_f = {
        "title": "Senior PHP Developer",
        "company": "PhpCo",
        "location": "Worldwide",
        "description": "Async work with Laravel and MySQL.",
        "tags": ["php", "laravel"],
        "salary_min": 70000,
        "salary_max": 90000,
        "posted_at": "2026-09-26T08:00:00+00:00",
    }

    prefs = {
        "roles": {
            "selected": ["python_scraper", "ai_model_trainer"],
            "custom_tags": [],
            "match_mode": "any",
        },
        "strict_no_phone": True,
        "async_first_no_spyware": True,
        "ignore_degree_requirement": True,
        "salary": {"enabled": False},
        "freshness_hours": 48,
        "geo": {"remote_worldwide_only": True, "excluded_regions": []},
        "blocklist": {"companies": [], "keywords": []},
        "allowlist": {"companies": []},
    }

    cases = [
        ("A (Python async worldwide) → PASS", job_a, True),
        ("B (call center) → REJECT (No-Phone)", job_b, False),
        ("C (Time Doctor spyware) → REJECT (Anti-Spyware)", job_c, False),
        ("D (10 dni stare) → REJECT (Freshness)", job_d, False),
        ("E (US Only) → REJECT (Geo)", job_e, False),
        ("F (PHP dev) → REJECT (Roles)", job_f, False),
    ]

    print("=== TEST FILTERS ===\n")
    all_passed = True
    for name, job, expected in cases:
        result = apply_filters(job, prefs)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {name}  (oczekiwano={expected}, otrzymano={result})")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 Wszystkie testy przeszły!")
        return 0
    print("🔴 Część testów nie przeszła.")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())