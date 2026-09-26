import os
import json
from dotenv import load_dotenv
from jobradar.llm import analyze_job

# Wczytanie kluczy z pliku .env
load_dotenv()

# Złośliwa oferta, która powinna zebrać sporo punktów ujemnych
sample_job = {
    "title": "Customer Support Representative",
    "company": "Toxic Corp",
    "description": "Szukamy osoby do obsługi klienta. Wymagana doskonała dykcja i obsługa połączeń przychodzących na słuchawce przez 8 godzin dziennie. Do monitorowania czasu pracy używamy Hubstaff z losowymi zrzutami ekranu. Widełki: 4000-5000 PLN."
}

print("Wysyłam zapytanie do Gemini...")
try:
    wynik = analyze_job(sample_job)
    print("\n--- SUKCES! Odpowiedź od AI ---")
    print(json.dumps(wynik, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n--- BŁĄD ---")
    print(str(e))