# Job Radar

**Automatyczny monitoring i raportowanie ofert pracy zdalnej z audytem jakościowym LLM.**

Job Radar codziennie skanuje 4 globalne portale pracy zdalnej, odsiewa duplikaty i oferty niepasujące, a następnie wykorzystuje Google Gemini (LLM) do audytu jakościowego każdego ogłoszenia — wykrywając ukryte call center, oprogramowanie szpiegujące i brak przejrzystości wynagrodzeń. Wyniki trafiają do spersonalizowanego raportu e-mail.

**Zero kosztów operacyjnych:** projekt działa w 100% na darmowych planach GitHub Actions, Supabase, Google Gemini i Resend.

---

## Spis treści

- [Job Radar](#job-radar)
  - [Spis treści](#spis-treści)
  - [Funkcje](#funkcje)
    - [Unikalne filtry jakościowe (przewaga rynkowa)](#unikalne-filtry-jakościowe-przewaga-rynkowa)
    - [Reszta funkcji](#reszta-funkcji)
  - [Architektura](#architektura)
  - [Wymagania](#wymagania)
  - [Instalacja](#instalacja)
    - [1. Klonowanie repo](#1-klonowanie-repo)
- [Windows:](#windows)
- [Linux/macOS:](#linuxmacos)
- [Test konfiguracji](#test-konfiguracji)
- [Test połączenia z bazą](#test-połączenia-z-bazą)
- [Test źródła (np. RemoteOK)](#test-źródła-np-remoteok)
- [Pełny pipeline](#pełny-pipeline)

---

## Funkcje

### Unikalne filtry jakościowe (przewaga rynkowa)

1. **No-Phone Guarantee** — LLM wykrywa manipulacje słowne maskujące call center („doskonała dykcja", „obsługa połączeń przychodzących", „dynamiczne środowisko telefoniczne").
2. **Anti-Spyware & Async-First** — wykrywanie wymogów instalacji oprogramowania monitorującego (Time Doctor, Hubstaff, screenshoty, keylogger, kamera).
3. **Przejrzystość stawek** — odrzucanie ofert bez jawnych widełek lub opartych o nieuczciwe formułki („wynagrodzenie zależne od zaangażowania").
4. **Świeżość i geolokalizacja** — filtry wieku ofert (24h / 48h / 7 dni) i „Worldwide only".

### Reszta funkcji

- **4 źródła danych** — RemoteOK, Remotive, Jobicy, WeWorkRemotely (API + RSS).
- **Bezhasłowy dostęp** — token `sec_...` w URL fragment, wymiana na `session_token` (httpOnly w sessionStorage).
- **Panel konfiguracji WWW** — 18 ról, 8 filtrów, widełki, blocklist, webhook Teams.
- **Deduplikacja między-źródłowa** — fingerprint SHA-256 z (firma|tytuł|lokalizacja|widełki).
- **Cache LLM** — te same oferty = 1 wywołanie Gemini (oszczędność limitów).
- **Fallback modeli** — automatyczne przełączanie przy 429/5xx.
- **Sentry** — opcjonalny monitoring błędów.
- **GitHub Actions** — cron 7:00 UTC codziennie + ręczne uruchamianie.

---

## Architektura

┌──────────────────────────────────────────────────────────────────┐
│ GitHub Actions (cron) │
│ 7:00 UTC codziennie │
└──────────────────────────┬───────────────────────────────────────┘
▼
┌──────────────────────────────────────────────────────────────────┐
│ Python Pipeline (jobradar/) │
│ │
│ 1. Fetch (4 sources) → 2. Dedup (fingerprint) │
│ 3. seen_jobs filter → 4. Hard filters (filters.py) │
│ 5. LLM audit (Gemini) → 6. Cache (llm_cache) │
│ 7. Digest HTML → 8. Send (Resend) │
└──────────────────────────┬───────────────────────────────────────┘
▼
┌──────────────────────────────────────────────────────────────────┐
│ Supabase (PostgreSQL, free tier) │
│ │
│ user_profiles – konta + preferences (JSONB) │
│ user_sessions – sesje (30 dni) │
│ seen_jobs – historia wysłanych ofert (per-user) │
│ pipeline_runs – logi uruchomień │
│ llm_cache – cache odpowiedzi Gemini │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ Edge Functions (Deno, Supabase, 500k wywołań/mies.) │
│ │
│ api-profile – rejestracja + wysyłka maila weryfikacyjnego │
│ api-session – wymiana token → session_token │
│ api-preferences – GET/PUT preferencji │
│ api-reset-seen-jobs – czyszczenie historii │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ Frontend (GitHub Pages, statyczny HTML/JS) │
│ │
│ index.html – panel rejestracji + konfiguracji │
│ config.html – przekierowanie z linku mailowego │
└──────────────────────────────────────────────────────────────────┘

text

---

## Wymagania

- **Python** 3.12+
- **Konto Supabase** (free tier) — baza + Edge Functions
- **Google AI Studio** (free tier) — klucz Gemini (`AQ.Ab8...` lub `AIzaSy...`)
- **Resend** (free tier, 3000 maili/mies.) — wysyłka e-maili
- **GitHub** — repo + Actions

---

## Instalacja

### 1. Klonowanie repo

```bash
git clone https://github.com/kasperstan1-boop/job-radar.git
cd job-radar
2. Wirtualne środowisko
bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
3. Zależności
bash
pip install -r requirements.txt
4. Konfiguracja Supabase
Utwórz projekt na supabase.com. W SQL Editor uruchom:

sql
-- user_profiles
create table user_profiles (
  id                 uuid primary key default gen_random_uuid(),
  config_token_hash  text unique not null,
  email              text not null,
  email_verified     boolean default false,
  preferences        jsonb not null default '{}'::jsonb,
  schema_version     int  not null default 1,
  created_at         timestamptz default now(),
  updated_at         timestamptz default now(),
  last_digest_at     timestamptz,
  is_active          boolean default true,
  deleted_at         timestamptz
);
create index on user_profiles using gin (preferences);
create index on user_profiles (is_active) where is_active = true;

-- user_sessions
create table user_sessions (
  session_token_hash text primary key,
  user_id            uuid not null references user_profiles(id) on delete cascade,
  created_at         timestamptz default now(),
  expires_at         timestamptz not null,
  last_used_at       timestamptz
);
create index on user_sessions (user_id);
create index on user_sessions (expires_at);

-- seen_jobs
create table seen_jobs (
  token_hash      text not null,
  job_fingerprint text not null,
  sent_at         timestamptz default now(),
  primary key (token_hash, job_fingerprint)
);
create index on seen_jobs (sent_at);

-- pipeline_runs
create table pipeline_runs (
  run_id          uuid primary key,
  started_at      timestamptz default now(),
  finished_at     timestamptz,
  status          text,
  source_stats    jsonb,
  llm_calls       int,
  llm_cost_usd    numeric(10,4),
  llm_models_used jsonb,
  error           text
);

-- llm_cache
create table llm_cache (
  job_fingerprint text primary key,
  result          jsonb not null,
  model_used      text,
  created_at      timestamptz default now()
);
5. Edge Functions
bash
supabase link --project-ref <TWOJ-PROJECT-REF>
supabase functions deploy api-profile
supabase functions deploy api-session
supabase functions deploy api-preferences
supabase functions deploy api-reset-seen-jobs
Sekrety w Supabase (Edge Functions → Secrets):

RESEND_API_KEY — klucz Resend (re_...)

Wyłącz verify_jwt dla api-profile i api-session (Settings → Enforce JWT Verification: OFF).

Konfiguracja
Skopiuj .env.example do .env i uzupełnij:

bash
cp .env.example .env
Zmienne w .env:

Zmienna	Opis	Gdzie znaleźć
SUPABASE_URL	https://<ref>.supabase.co	Supabase → Settings → API
SUPABASE_SERVICE_KEY	sb_secret_... (nowy) lub eyJ... (legacy)	Supabase → Settings → API
GEMINI_API_KEY	AQ.Ab8... lub AIzaSy...	aistudio.google.com
RESEND_API_KEY	re_...	resend.com/api-keys
NOTIFICATION_EMAIL	Twój e-mail (musi być zweryfikowany w Resend)	—
TEAMS_WEBHOOK_URL	opcjonalne, webhook Teams	Teams → Workflows
SENTRY_DSN	opcjonalne, monitoring błędów	sentry.io
Uwaga o Resend: w darmowym planie bez własnej domeny można wysyłać tylko na adres, którym zarejestrowałeś konto Resend.

Uruchomienie
Lokalnie
bash
# Test konfiguracji
python -m jobradar.config

# Test połączenia z bazą
python -m jobradar.db

# Test źródła (np. RemoteOK)
python -m jobradar.sources.remoteok

# Pełny pipeline
python -m jobradar.pipeline
GitHub Actions
Pipeline uruchamia się automatycznie codziennie o 7:00 UTC. Ręcznie:

GitHub → Actions → Job Radar Digest

Kliknij Run workflow

Sekrety w GitHub (Settings → Secrets and variables → Actions):

SUPABASE_URL

SUPABASE_SERVICE_KEY

GEMINI_API_KEY

RESEND_API_KEY

NOTIFICATION_EMAIL

Frontend
Otwórz kasperstan1-boop.github.io/job-radar, wpisz e-mail — link dostępowy przyjdzie na skrzynkę.

Struktura projektu
text
job-radar/
├── .github/workflows/digest.yml     # GitHub Actions cron
├── frontend/
│   ├── index.html                   # Panel rejestracji + konfiguracji
│   └── config.html                  # Przekierowanie z linku mailowego
├── jobradar/
│   ├── config.py                    # Zmienne środowiskowe, stałe
│   ├── fingerprint.py               # SHA-256 dedup
│   ├── filters.py                   # 8 filtrów twardych
│   ├── llm.py                       # Gemini + fallback modeli
│   ├── prompt.py                    # Prompt + response_schema
│   ├── digest.py                    # Generator HTML + plain text
│   ├── notifier.py                  # Resend + Teams webhook
│   ├── db.py                        # Klient Supabase
│   ├── pipeline.py                  # Orkiestrator
│   └── sources/
│       ├── remoteok.py              # Publiczne API JSON
│       ├── remotive.py              # Publiczne API JSON
│       ├── jobicy.py                # Publiczne API JSON
│       └── wwr.py                   # Kanały RSS
├── supabase/functions/
│   ├── api-profile/index.ts         # Rejestracja + mail weryfikacyjny
│   ├── api-session/index.ts         # Wymiana token → session_token
│   ├── api-preferences/index.ts     # GET/PUT preferencji
│   └── api-reset-seen-jobs/index.ts # Reset historii
├── tests/
│   ├── test_fingerprint.py          # Test dedup
│   ├── test_filters.py              # Test filtrów (6 przypadków)
│   ├── test_all_sources.py          # Test 4 scraperów
│   ├── dry_run.py                   # Dry run bez LLM
│   └── eval_dataset/
│       ├── eval_jobs.json           # 20 ofert (Golden Dataset)
│       └── eval_prompts.py          # Ewaluacja promptu (Precision/Recall/F1)
├── examples/
│   └── digest_example.html          # Przykładowy raport
├── .env.example
├── requirements.txt
└── README.md
Jak dodać nowe źródło
Krok 1: Utwórz jobradar/sources/<nazwa>.py:

python
import logging
from typing import Any
import requests

logger = logging.getLogger(__name__)
API_URL = "https://example.com/api/jobs"

def fetch_jobs() -> list[dict[str, Any]]:
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error("Błąd: %s", e)
        return []

    return [{
        "source": "example",
        "id": str(item.get("id", "")),
        "title": item.get("title", ""),
        "company": item.get("company", ""),
        "location": item.get("location", ""),
        "url": item.get("url", ""),
        "tags": item.get("tags", []),
        "description": item.get("description", ""),
        "salary_min": item.get("salary_min"),
        "salary_max": item.get("salary_max"),
        "posted_at": item.get("posted_at", ""),
    } for item in data.get("jobs", [])]
Krok 2: Dodaj do jobradar/config.py:

python
SOURCES: Final[tuple[str, ...]] = ("remoteok", "remotive", "jobicy", "wwr", "example")
Krok 3: Dodaj do jobradar/pipeline.py:

python
from jobradar.sources import example

SOURCE_FETCHERS = {
    "remoteok": remoteok.fetch_jobs,
    ...
    "example": example.fetch_jobs,
}
Krok 4: Test:

bash
python -m jobradar.sources.example
Pipeline automatycznie:

Deduplikuje oferty z nowego źródła

Przepuści przez filtry i LLM

Uwzględni w digestcie

Testy i ewaluacja
Testy jednostkowe
bash
python -m tests.test_fingerprint
python -m tests.test_filters
python -m tests.test_all_sources
Dry run (bez wywołań LLM)
bash
python -m tests.dry_run
Ewaluacja promptu (Golden Dataset — 20 ofert)
bash
python -m tests.eval_dataset.eval_prompts
python -m tests.eval_dataset.eval_prompts --verbose
python -m tests.eval_dataset.eval_prompts --threshold 0.90
Metryki (ostatni run):

Filtr	Precision	Recall	F1
No-Phone Guarantee	100%	100%	100%
Async-Friendly	100%	90%	94.7%
Salary Disclosed	100%	100%	100%
Koszty
Wszystko w darmowych planach:

Usługa	Limit free tier	Wykorzystanie
GitHub Actions	2000 min/mies.	~5 min/dzień
Supabase (baza)	500 MB, 2 GB transfer	<10 MB
Supabase Edge Functions	500k wywołań/mies.	~30/dzień
Google Gemini	15 RPM, 500–1500 RPD	~31/dzień
Resend	3000 maili/mies.	1/dzień
GitHub Pages	unlimited	—
Koszt miesięczny: 0,00 USD.

Licencja
MIT — używaj, modyfikuj, sprzedawaj. Kod dostarczony bez gwarancji.
```
