"""Dry run: fetch → dedup → filters → raport (BEZ LLM)."""
import logging
from collections import Counter

from jobradar.db import get_db
from jobradar.filters import apply_filters
from jobradar.fingerprint import generate_fingerprint
from jobradar.pipeline import dedup_between_sources, fetch_all_jobs, get_active_user

logging.basicConfig(level=logging.WARNING)


def main():
    db = get_db()

    # ── Użytkownik ──
    user = get_active_user(db)
    if not user:
        print("❌ Brak aktywnego użytkownika.")
        return
    print(f"Użytkownik: {user['email']}")
    print(f"Token hash: {user['config_token_hash'][:16]}...")
    print(f"freshness_hours: {user['preferences'].get('freshness_hours')}")
    print()

    # ── Fetch + dedup ──
    raw, stats = fetch_all_jobs(db)
    print(f"Pobrano: {len(raw)} ofert")
    for name, status in stats.items():
        print(f"  {name:12} {status}")
    print()

    unique = dedup_between_sources(raw)
    print(f"Po dedupie: {len(unique)} ofert\n")

    # ── Filtry (bez zapisu do seen_jobs) ──
    passing = []
    for job in unique:
        clean = {k: v for k, v in job.items() if not k.startswith("_")}
        if apply_filters(clean, user["preferences"]):
            passing.append(clean)

    print(f"═══ PRZESZŁO FILTRY: {len(passing)} / {len(unique)} ═══\n")

    # ── Rozkład ──
    sources = Counter(j.get("source", "?") for j in passing)
    print("Per źródło:")
    for src, cnt in sources.most_common():
        print(f"  {src:12} {cnt}")

    # ── 15 pierwszych tytułów ──
    print("\n15 pierwszych ofert:")
    for j in passing[:15]:
        print(f"  [{j.get('source')}] {j.get('title', '')[:60]} @ {j.get('company', '')[:30]}")

    print(f"\n💰 Szacunkowy koszt LLM: 0 tokenów (nic nie wywołaliśmy)")
    print(f"📊 Realnie: {len(passing)} wywołań Gemini = ~{len(passing) * 4} sekund")


if __name__ == "__main__":
    main()