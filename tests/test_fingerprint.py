"""
Test modułu jobradar.fingerprint — weryfikacja dedup między-źródłowego.
Uruchomienie: python -m tests.test_fingerprint
"""
from jobradar.fingerprint import generate_fingerprint, normalize_text


def main():
    # ── Przypadek 1: identyczne oferty → ten sam hash ──
    job_a = {
        "company": "Acme Corp.",
        "title": "Senior Python Developer",
        "location": "Worldwide",
        "salary_min": 80000,
        "salary_max": 120000,
    }
    job_a2 = {
        "company": "ACME  CORP",         # inny case + spacja
        "title": "senior python developer",  # inny case
        "location": "worldwide",         # inny case
        "salary_min": 80000,
        "salary_max": 120000,
    }
    # ── Przypadek 2: inna firma → inny hash ──
    job_b = {
        "company": "Globex",
        "title": "React Developer",
        "location": "Worldwide",
        "salary_min": 60000,
        "salary_max": 90000,
    }
    # ── Przypadek 3: ta sama firma, inny tytuł → inny hash ──
    job_c = {
        "company": "Acme Corp.",
        "title": "DevOps Engineer",       # inny tytuł
        "location": "Worldwide",
        "salary_min": 80000,
        "salary_max": 120000,
    }
    # ── Przypadek 4: brak widełek → "unknown" bucket ──
    job_d = {
        "company": "Acme Corp.",
        "title": "Senior Python Developer",
        "location": "Worldwide",
        # brak salary_min/salary_max
    }

    fp_a = generate_fingerprint(job_a)
    fp_a2 = generate_fingerprint(job_a2)
    fp_b = generate_fingerprint(job_b)
    fp_c = generate_fingerprint(job_c)
    fp_d = generate_fingerprint(job_d)

    print("=== TEST FINGERPRINT ===\n")
    print(f"A  (Acme/Python/WW/80-120): {fp_a[:16]}...")
    print(f"A' (Acme/Python/WW/80-120): {fp_a2[:16]}...")
    print(f"B  (Globex/React/WW/60-90): {fp_b[:16]}...")
    print(f"C  (Acme/DevOps/WW/80-120): {fp_c[:16]}...")
    print(f"D  (Acme/Python/WW/brak)  : {fp_d[:16]}...")
    print()

    # ── Asercje ──
    results = []

    results.append((
        "A == A' (dedup działa)",
        fp_a == fp_a2,
    ))
    results.append((
        "A != B (różne firmy)",
        fp_a != fp_b,
    ))
    results.append((
        "A != C (ta sama firma, inny tytuł)",
        fp_a != fp_c,
    ))
    results.append((
        "A != D (brak widełek)",
        fp_a != fp_d,
    ))

    # ── Raport ──
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 Wszystkie testy przeszły!")
        return 0
    else:
        print("🔴 Część testów nie przeszła.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())