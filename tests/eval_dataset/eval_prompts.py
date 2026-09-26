"""
eval_prompts.py — Ewaluacja promptu LLM dla Job Radar.

Uruchomienie:
    python tests/eval_dataset/eval_prompts.py
    python tests/eval_dataset/eval_prompts.py --verbose
    python tests/eval_dataset/eval_prompts.py --threshold 0.90

Wyjście:
    - Wydruk metryk w terminalu (Accuracy, Precision, Recall, F1 dla 3 filtrów).
    - Zapis do eval_results.json z timestampem (do śledzenia regresji).
    - Exit code 0 (PASS) lub 1 (FAIL) — do użycia w GitHub Actions.

Zależności: WYŁĄCZNIE biblioteka standardowa Pythona.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Import analyze_job z projektu. Jeśli uruchamiasz z innego katalogu,
# upewnij się, że root projektu jest w PYTHONPATH.
from jobradar.llm import analyze_job


# ─────────────────────────────────────────────────────────────────────────────
# 1. METRYKI — czysty Python, bez scikit-learn / numpy / pandas
# ─────────────────────────────────────────────────────────────────────────────

def calculate_metrics(y_true: list[bool], y_pred: list[bool]) -> dict:
    """Liczy Accuracy, Precision, Recall, F1 na podstawie etykiet prawdziwych i przewidzianych."""
    if not y_true or len(y_true) != len(y_pred):
        return {
            "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
            "tp": 0, "fp": 0, "fn": 0, "tn": 0, "support": 0,
        }

    tp = sum(t and p for t, p in zip(y_true, y_pred))
    fp = sum(not t and p for t, p in zip(y_true, y_pred))
    fn = sum(t and not p for t, p in zip(y_true, y_pred))
    tn = sum(not t and not p for t, p in zip(y_true, y_pred))

    accuracy = (tp + tn) / len(y_true) if y_true else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "support": len(y_true),
    }


def print_metrics(name: str, m: dict, verbose: bool = False) -> None:
    """Wypisuje metryki w czytelnej formie."""
    print(f"\n=== {name} ===")
    print(f"  Accuracy:  {m['accuracy']:.2%}")
    print(f"  Precision: {m['precision']:.2%}")
    print(f"  Recall:    {m['recall']:.2%}")
    print(f"  F1:        {m['f1']:.2%}")
    if verbose:
        print(f"  TP={m['tp']}, FP={m['fp']}, FN={m['fn']}, TN={m['tn']}, "
              f"support={m['support']}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADAPTER — obsługa płaskiej i zagnieżdżonej struktury odpowiedzi LLM
# ─────────────────────────────────────────────────────────────────────────────

def extract_fields(result: dict | None) -> dict:
    """
    Wyciąga pola z odpowiedzi analyze_job.
    Obsługuje:
      - strukturę płaską:  {"phone_signals": [...], "spyware_signals": [...], ...}
      - strukturę zagnieżdżoną: {"result": {"phone_signals": [...], ...}}
      - None / pusty dict → zwraca bezpieczne wartości domyślne

    Zwraca dict z kluczami:
      phone_signals, spyware_signals, salary_disclosed, score, summary
    """
    safe_default = {
        "phone_signals": [],
        "spyware_signals": [],
        "salary_disclosed": False,
        "score": None,
        "summary": None,
    }

    if not result or not isinstance(result, dict):
        return safe_default

    # Jeśli jest klucz "result" i jest to dict → użyj zagnieżdżenia
    payload = result.get("result") if isinstance(result.get("result"), dict) else result

    return {
        "phone_signals":   payload.get("phone_signals")   or [],
        "spyware_signals": payload.get("spyware_signals") or [],
        "salary_disclosed": bool(payload.get("salary_disclosed", False)),
        "score":   payload.get("score"),
        "summary": payload.get("summary"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. GŁÓWNA LOGIKA EWALUACJI
# ─────────────────────────────────────────────────────────────────────────────

def run_eval(threshold: float = 0.95, verbose: bool = False) -> int:
    """
    Uruchamia ewaluację. Zwraca exit code:
      0 = PASS (wszystkie filtry >= threshold)
      1 = FAIL
      2 = błąd techniczny (brak pliku, błąd JSON)
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "eval_jobs.json")
    results_path = os.path.join(current_dir, "eval_results.json")

    # ── Wczytanie zestawu testowego ──
    if not os.path.exists(json_path):
        print(f"❌ Błąd: nie znaleziono pliku {json_path}", file=sys.stderr)
        return 2

    print(f"Wczytuję dane z: {json_path}")
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Błąd parsowania JSON: {e}", file=sys.stderr)
        return 2

    jobs = data.get("jobs", [])
    if not jobs:
        print("❌ Błąd: zestaw testowy jest pusty.", file=sys.stderr)
        return 2

    # ── Trzy niezależne zbiory etykiet ──
    y_true_phone,  y_pred_phone  = [], []
    y_true_async,  y_pred_async  = [], []
    y_true_salary, y_pred_salary = [], []

    per_job_results = []
    errors = 0

    for job in jobs:
        job_id = job.get("id", "?")
        text = job.get("text", "")
        gt = job.get("ground_truth", {})

        print(f"Analizuję ofertę ID: {job_id}...", end=" ")

        # analyze_job przyjmuje string (zgodnie z sygnaturą w llm.py)
        try:
            raw_result = analyze_job({"description": text, "title": "Brak", "company": "Brak"})
            fields = extract_fields(raw_result)
            print("OK")
        except Exception as e:
            print(f"BŁĄD: {e}")
            errors += 1
            fields = extract_fields(None)

        # ── Filtr 1: No-Phone ──
        # is_no_phone = True → oczekujemy ZERO sygnałów telefonicznych
        has_no_phone = len(fields["phone_signals"]) == 0
        y_true_phone.append(bool(gt.get("is_no_phone", False)))
        y_pred_phone.append(has_no_phone)

        # ── Filtr 2: Anti-Spyware ──
        # is_async_friendly = True → oczekujemy ZERO sygnałów spyware
        has_no_spyware = len(fields["spyware_signals"]) == 0
        y_true_async.append(bool(gt.get("is_async_friendly", False)))
        y_pred_async.append(has_no_spyware)

        # ── Filtr 3: Salary disclosed ──
        y_true_salary.append(bool(gt.get("salary_disclosed", False)))
        y_pred_salary.append(fields["salary_disclosed"])

        # ── Per-job zapis (dla raportu) ──
        per_job_results.append({
            "id": job_id,
            "ground_truth": gt,
            "predicted": {
                "is_no_phone": has_no_phone,
                "is_async_friendly": has_no_spyware,
                "salary_disclosed": fields["salary_disclosed"],
            },
            "llm_raw": {
                "score": fields["score"],
                "summary": fields["summary"],
                "phone_signals": fields["phone_signals"],
                "spyware_signals": fields["spyware_signals"],
            } if verbose else None,
        })

    # ── Obliczenie metryk ──
    metrics_phone  = calculate_metrics(y_true_phone,  y_pred_phone)
    metrics_async  = calculate_metrics(y_true_async,  y_pred_async)
    metrics_salary = calculate_metrics(y_true_salary, y_pred_salary)

    print("\n" + "=" * 60)
    print("WYNIKI EWALUACJI")
    print("=" * 60)
    print_metrics("No-Phone Guarantee", metrics_phone,  verbose)
    print_metrics("Anti-Spyware",       metrics_async,  verbose)
    print_metrics("Salary Disclosed",   metrics_salary, verbose)

    if errors > 0:
        print(f"\n⚠️  Wystąpiły {errors} błędów podczas analizy ofert.")

    # ── Zapis wyników do pliku ──
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": json_path,
            "jobs_count": len(jobs),
            "errors_count": errors,
        },
        "threshold": threshold,
        "metrics": {
            "no_phone":        metrics_phone,
            "anti_spyware":    metrics_async,
            "salary_disclosed": metrics_salary,
        },
        "per_job": per_job_results,
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Raport zapisany do: {results_path}")

    # ── Decyzja PASS / FAIL ──
    failed_filters = []
    if metrics_phone["precision"]  < threshold: failed_filters.append("No-Phone")
    if metrics_async["precision"]  < threshold: failed_filters.append("Anti-Spyware")
    if metrics_salary["precision"] < threshold: failed_filters.append("Salary Disclosed")

    print("\n" + "=" * 60)
    if failed_filters:
        print(f"❌ FAIL: Precision < {threshold:.0%} dla filtrów: {', '.join(failed_filters)}")
        return 1
    else:
        print(f"✅ PASS: wszystkie filtry mają Precision ≥ {threshold:.0%}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ewaluacja promptu LLM dla Job Radar.")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="Minimalny Precision (0.0-1.0). Domyślnie 0.95.")
    parser.add_argument("--verbose", action="store_true",
                        help="Wypisuje szczegóły per oferta i zapisuje LLM raw do raportu.")
    args = parser.parse_args()

    exit_code = run_eval(threshold=args.threshold, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()