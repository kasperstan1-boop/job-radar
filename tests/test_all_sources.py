"""Test wszystkich scraperów — sprawdza kontrakt pól."""
from jobradar.sources import remoteok, remotive, jobicy


EXPECTED_FIELDS = {
    "source", "id", "title", "company", "location",
    "url", "tags", "description", "salary_min", "salary_max", "posted_at",
}


def check_source(name: str, fetch_fn) -> bool:
    print(f"\n=== {name.upper()} ===")
    jobs = fetch_fn()

    if not jobs:
        print(f"❌ {name}: 0 ofert — API mogło być niedostępne")
        return False

    print(f"✅ {name}: pobrano {len(jobs)} ofert")

    # Sprawdź kontrakt pól na pierwszej ofercie
    sample = jobs[0]
    missing = EXPECTED_FIELDS - set(sample.keys())
    if missing:
        print(f"❌ {name}: brakuje pól: {sorted(missing)}")
        return False
    print(f"✅ {name}: kontrakt pól OK")

    # Sprawdź ile ofert ma widełki i datę
    with_salary = sum(1 for j in jobs if j.get("salary_min") or j.get("salary_max"))
    with_date = sum(1 for j in jobs if j.get("posted_at"))
    print(f"   ofert z widełkami: {with_salary}/{len(jobs)}")
    print(f"   ofert z datą:      {with_date}/{len(jobs)}")
    print(f"   przykładowy tytuł: {sample['title'][:70]}")
    print(f"   przykładowa data:  {sample['posted_at']!r}")
    print(f"   przykładowe salary: min={sample['salary_min']}, max={sample['salary_max']}")
    return True


def main():
    from jobradar.sources import wwr  # noqa: PLC0415

    results = [
        ("RemoteOK", remoteok.fetch_jobs),
        ("Remotive", remotive.fetch_jobs),
        ("Jobicy",   jobicy.fetch_jobs),
        ("WWR",      wwr.fetch_jobs),
    ]

    print("=== TEST WSZYSTKICH ŹRÓDEŁ ===\n")
    outcomes = []
    for name, fn in results:
        try:
            outcomes.append(check_source(name, fn))
        except Exception as e:  # noqa: BLE001
            print(f"❌ {name}: wyjątek — {e}")
            outcomes.append(False)

    print("\n=== PODSUMOWANIE ===")
    passed = sum(outcomes)
    total = len(outcomes)
    print(f"Zaliczone: {passed}/{total}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())