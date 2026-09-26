"""Diagnostyka: który filtr odrzuca oferty?"""
import logging
from collections import Counter

from jobradar.db import get_db
from jobradar.filters import (
    _check_allowlist, _check_blocklist, _check_freshness, _check_geo,
    _check_roles, _check_salary, _check_strict_no_phone, _check_async_no_spyware,
)
from jobradar.sources import remoteok, remotive, jobicy, wwr

logging.basicConfig(level=logging.WARNING)


def main():
    db = get_db()
    user = (
        db.table("user_profiles")
        .select("email, preferences")
        .eq("is_active", True)
        .limit(1)
        .execute()
    ).data[0]
    prefs = user.get("preferences") or {}
    print(f"Użytkownik: {user['email']}")
    print(f"Preferencje:")
    print(f"  roles.selected:      {prefs.get('roles', {}).get('selected')}")
    print(f"  strict_no_phone:     {prefs.get('strict_no_phone')}")
    print(f"  async_first_no_spyware: {prefs.get('async_first_no_spyware')}")
    print(f"  freshness_hours:     {prefs.get('freshness_hours')}")
    print(f"  geo:                 {prefs.get('geo')}")
    print(f"  salary:              {prefs.get('salary')}")
    print()

    # Pobierz oferty z 4 źródeł
    all_jobs = []
    for name, fn in [("remoteok", remoteok.fetch_jobs),
                     ("remotive", remotive.fetch_jobs),
                     ("jobicy", jobicy.fetch_jobs),
                     ("wwr", wwr.fetch_jobs)]:
        try:
            jobs = fn()
            all_jobs.extend(jobs)
            print(f"  {name}: {len(jobs)} ofert")
        except Exception as e:
            print(f"  {name}: BŁĄD — {e}")

    print(f"\nRAZEM: {len(all_jobs)} ofert\n")

    # Test per filtr na WSZYSTKICH ofertach
    filters = [
        ("blocklist", _check_blocklist),
        ("allowlist", _check_allowlist),
        ("roles", _check_roles),
        ("strict_no_phone", _check_strict_no_phone),
        ("async_no_spyware", _check_async_no_spyware),
        ("geo", _check_geo),
        ("salary", _check_salary),
        ("freshness", _check_freshness),
    ]

    print("=== ILE OFERT PRZECHODZI PRZEZ KAŻDY FILTR OSOBNO ===\n")
    for name, fn in filters:
        passed = sum(1 for job in all_jobs if fn(job, prefs))
        pct = 100 * passed / len(all_jobs) if all_jobs else 0
        print(f"  {name:25} {passed:4}/{len(all_jobs)}  ({pct:5.1f}%)")

    # Które filtry odrzucają najwięcej
    print("\n=== PIERWSZE 3 OFERTY — CO ODRZUCA ===")
    for job in all_jobs[:3]:
        print(f"\n--- {job['title'][:60]} @ {job['company'][:30]} ---")
        for name, fn in filters:
            ok = fn(job, prefs)
            print(f"  {'✅' if ok else '❌'} {name}")
        print(f"  location={job.get('location')!r}")
        print(f"  posted_at={job.get('posted_at')!r}")
        print(f"  tags={job.get('tags')[:5] if job.get('tags') else []}")


if __name__ == "__main__":
    main()