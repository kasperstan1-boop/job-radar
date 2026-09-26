<div align="center">

# 📡 Job Radar

**Autonomous remote job market monitoring with LLM-powered quality audit.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cron-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Gemini](https://img.shields.io/badge/Gemini-AI-8E7CC3?logo=google&logoColor=white)](https://ai.google.dev/)
[![Resend](https://img.shields.io/badge/Resend-Email-FF6B6B?logo=resend&logoColor=white)](https://resend.com/)
[![100% Free](https://img.shields.io/badge/Cost-0%20USD-brightgreen)](https://github.com/kasperstan1-boop/job-radar)

</div>

---

Job Radar scans 4 global remote job boards every day, filters out duplicates and irrelevant offers, then uses **Google Gemini (LLM)** to perform a quality audit of each posting — detecting hidden call centers, surveillance software requirements, and lack of salary transparency. Results are delivered to a personalized email digest.

> **💡 Project philosophy:** We filter job offers through the lens of **remote worker quality of life**, not just keywords. This is our USP against LinkedIn and Indeed.

**[🚀 Quick start](#-quick-start) · [✨ Features](#-features) · [🏗️ Architecture](#️-architecture) · [📂 Project structure](#-project-structure) · [📄 License](#-license)**

---

## 💭 A note on scope and design decisions

**This project is deliberately built as a minimum viable version — but a fully working one.**

The original vision was significantly more ambitious: dozens of job boards across multiple industries, support for a much wider range of positions (including niche domains such as **trading, iGaming, analytics, and specialized technical roles**), the ability to **select job agencies as data sources**, richer filtering by contract type and timezone, and multi-user teams.

However, I made a deliberate architectural decision:

> **Every single component must run for exactly $0.00 USD per month, forever — using only the free tiers of GitHub Actions, Supabase, Google Gemini, and Resend.**

This constraint forced me to strip the system down to the absolute minimum viable implementation, while still preserving everything that makes Job Radar useful. Every design choice — the number of sources, the LLM throttle, the size of the digest, the retention policies — is calibrated so that **free cloud tiers never get exceeded**, and the accounts never get rate-limited or blocked.

In other words: this is not "a demo that stops working after one run". It is a **production-grade system that runs autonomously 24/7, costs nothing, and can be scaled up instantly** by removing a small number of configuration limits when budget becomes available.

**What would change with proper funding:**

| Area                  | MVP (this repo, $0)                               | Scaled-up version                                                           |
| --------------------- | ------------------------------------------------- | --------------------------------------------------------------------------- |
| **Sources**           | 4 global boards (RemoteOK, Remotive, Jobicy, WWR) | 15–30 boards, including niche iGaming, trading, and data-annotation portals |
| **Positions**         | 18 role tags across 4 pillars                     | Hundreds of role categories, dynamically extracted from postings            |
| **Agencies**          | Direct employer postings only                     | Ability to whitelist or block recruitment agencies as sources               |
| **LLM**               | Gemini Free Tier (throttled to ~120 calls/run)    | Dedicated Gemini paid tier — no throttle, 10× more offers processed per run |
| **Users**             | Single active user (MVP architecture)             | Multi-tenant SaaS with team accounts, shared digests, and role-based access |
| **Email delivery**    | `onboarding@resend.dev` sandbox                   | Verified custom domain, branded sender, higher monthly quota                |
| **Database**          | Supabase Free (500 MB)                            | Supabase Pro — unlimited growth, backups, and PITR                          |
| **Delivery channels** | Email + Teams webhook                             | + Slack, Telegram, Discord, RSS, mobile push notifications                  |
| **Scoring**           | Static prompt-based LLM audit                     | Personalized re-ranker trained on user feedback (👍/👎)                     |
| **Languages**         | English-only postings                             | Multi-language normalization and translation                                |

**The point:** every architectural decision in this repo is made so that _adding money later is a configuration change, not a rewrite_. The code, the schema, the abstractions, and the CI/CD pipeline are all ready for scale — they are only throttled at the surface level to stay free.

---

## 🎯 The problem we solve

Most remote job seekers waste hours manually scanning listings full of traps: hidden call centers disguised as "assistants", offers with no salary range, or toxic companies requiring surveillance software on your personal computer.

Job Radar automates this process and **eliminates 90% of the noise** — you only receive offers that match your quality criteria.

---

## ✨ Features

### Unique quality filters (market advantage)

| Filter                             | Description                                                                                                                             |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **📞 No-Phone Guarantee**          | LLM detects linguistic manipulation masking call centers ("excellent diction", "handling incoming calls", "dynamic phone environment"). |
| **🛡️ Anti-Spyware & Async-First**  | Detection of requirements to install monitoring software (Time Doctor, Hubstaff, screenshots, keylogger, webcam).                       |
| **💰 Salary transparency**         | Rejection of offers without explicit salary ranges or based on unfair wording ("pay dependent on engagement").                          |
| **📅 Freshness and geo-filtering** | Job age filters (24h / 48h / 7 days) and "Worldwide only".                                                                              |

### Everything else

| Feature                           | Description                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| **🌐 4 data sources**             | RemoteOK, Remotive, Jobicy, WeWorkRemotely (API + RSS).                                       |
| **🔐 Passwordless access**        | `sec_...` token in URL fragment, exchanged for `session_token` (httpOnly via sessionStorage). |
| **⚙️ Web configuration panel**    | 18 roles, 8 filters, salary range, blocklist, Teams webhook.                                  |
| **🔄 Cross-source deduplication** | SHA-256 fingerprint of (company\|title\|location\|salary).                                    |
| **⚡ LLM cache**                  | Same offers = 1 Gemini call (saves quota).                                                    |
| **🔁 Model fallback**             | Automatic switch on 429/5xx errors.                                                           |
| **📊 Sentry**                     | Optional error monitoring.                                                                    |
| **⏰ GitHub Actions**             | Cron at 7:00 UTC daily + manual trigger.                                                      |

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A[GitHub Actions<br/>Cron 7:00 UTC] --> B[Python Pipeline]
    B --> C{Fetch<br/>4 sources}
    C --> D[Dedup<br/>fingerprint]
    D --> E[seen_jobs filter]
    E --> F[Hard filters]
    F --> G[LLM audit<br/>Gemini]
    G --> H[Cache<br/>llm_cache]
    H --> I[Digest HTML]
    I --> J[Send<br/>Resend]

    B --> K[(Supabase<br/>PostgreSQL)]
    K --> L[user_profiles]
    K --> M[user_sessions]
    K --> N[seen_jobs]
    K --> O[pipeline_runs]
    K --> P[llm_cache]

    B --> Q[Edge Functions<br/>Deno]
    Q --> R[api-profile]
    Q --> S[api-session]
    Q --> T[api-preferences]
    Q --> U[api-reset-seen-jobs]

    V[Frontend<br/>GitHub Pages] --> W[index.html]
    V --> X[config.html]
```

**Tech stack:**

| Layer              | Technology                                                                 |
| ------------------ | -------------------------------------------------------------------------- |
| **Backend**        | Python 3.12, `google-genai`, `supabase-py`, `resend`, `bleach`, `requests` |
| **Database**       | Supabase (PostgreSQL)                                                      |
| **Edge Functions** | Deno (TypeScript)                                                          |
| **Frontend**       | HTML/CSS/JS (GitHub Pages)                                                 |
| **LLM**            | Google Gemini (Flash-Lite, Flash, Pro)                                     |
| **Email**          | Resend (REST API)                                                          |
| **CI/CD**          | GitHub Actions (cron + manual)                                             |
| **Monitoring**     | Sentry (optional)                                                          |

---

## 🚀 Quick start

### Requirements

- **Python** 3.12+
- **Supabase account** (free tier) — database + Edge Functions
- **Google AI Studio** (free tier) — Gemini API key (`AQ.Ab8...` or `AIzaSy...`)
- **Resend** (free tier, 3000 emails/month) — email delivery
- **GitHub** — repository + Actions

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/kasperstan1-boop/job-radar.git
cd job-radar

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# 3. Dependencies
pip install -r requirements.txt

# 4. Supabase setup (SQL Editor)
# Run the SQL script from the "Database schema" section below

# 5. Edge Functions
supabase link --project-ref <YOUR-PROJECT-REF>
supabase functions deploy api-profile
supabase functions deploy api-session
supabase functions deploy api-preferences
supabase functions deploy api-reset-seen-jobs

# 6. Run the pipeline
python -m jobradar.pipeline
```

<details>
<summary>📋 <strong>Database schema (click to expand)</strong></summary>

```sql
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

-- user_sessions
create table user_sessions (
  session_token_hash text primary key,
  user_id            uuid not null references user_profiles(id) on delete cascade,
  created_at         timestamptz default now(),
  expires_at         timestamptz not null,
  last_used_at       timestamptz
);

-- seen_jobs
create table seen_jobs (
  token_hash      text not null,
  job_fingerprint text not null,
  sent_at         timestamptz default now(),
  primary key (token_hash, job_fingerprint)
);

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
```

</details>

### Configuration

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable               | Description                                | Where to find                                             |
| ---------------------- | ------------------------------------------ | --------------------------------------------------------- |
| `SUPABASE_URL`         | `https://<ref>.supabase.co`                | Supabase → Settings → API                                 |
| `SUPABASE_SERVICE_KEY` | `sb_secret_...` (new) or `eyJ...` (legacy) | Supabase → Settings → API                                 |
| `GEMINI_API_KEY`       | `AQ.Ab8...` or `AIzaSy...`                 | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `RESEND_API_KEY`       | `re_...`                                   | [resend.com/api-keys](https://resend.com/api-keys)        |
| `NOTIFICATION_EMAIL`   | Your email (verified in Resend)            | —                                                         |
| `TEAMS_WEBHOOK_URL`    | optional Teams webhook                     | Teams → Workflows                                         |
| `SENTRY_DSN`           | optional error monitoring                  | [sentry.io](https://sentry.io)                            |

> [!WARNING]
> In the free Resend tier without your own domain, you can only send emails **to the address you registered your Resend account with**.

---

## 📂 Project structure

```text
job-radar/
├── .github/workflows/digest.yml     # GitHub Actions cron
├── frontend/
│   ├── index.html                   # Registration + configuration panel
│   └── config.html                  # Redirect from email link
├── jobradar/
│   ├── config.py                    # Environment variables, constants
│   ├── fingerprint.py               # SHA-256 deduplication
│   ├── filters.py                   # 8 hard filters
│   ├── llm.py                       # Gemini + model fallback
│   ├── prompt.py                    # Prompt + response_schema
│   ├── digest.py                    # HTML + plain text generator
│   ├── notifier.py                  # Resend + Teams webhook
│   ├── db.py                        # Supabase client
│   ├── pipeline.py                  # Orchestrator
│   └── sources/
│       ├── remoteok.py              # Public JSON API
│       ├── remotive.py              # Public JSON API
│       ├── jobicy.py                # Public JSON API
│       └── wwr.py                   # RSS feeds
├── supabase/functions/
│   ├── api-profile/index.ts         # Registration + verification email
│   ├── api-session/index.ts         # Token → session_token exchange
│   ├── api-preferences/index.ts     # GET/PUT preferences
│   └── api-reset-seen-jobs/index.ts # History reset
├── tests/
│   ├── test_fingerprint.py          # Dedup test
│   ├── test_filters.py              # Filter tests (6 cases)
│   ├── test_all_sources.py          # 4 scrapers test
│   └── eval_dataset/                # Golden Dataset (20 offers)
├── examples/
│   ├── digest_example.html          # Sample report (HTML)
│   └── digest_example.png           # Report screenshot
├── .env.example
├── requirements.txt
└── README.md
```

---

## 📄 Sample digest

Job Radar sends a personalized HTML report every day. Each offer includes an LLM score (0–100%), a 2-sentence summary, and red flags.

![Sample digest](examples/digest_example.png)

> The full HTML file is available at [`examples/digest_example.html`](examples/digest_example.html).

---

## 🧪 Tests and evaluation

```bash
# Unit tests
python -m tests.test_fingerprint
python -m tests.test_filters
python -m tests.test_all_sources

# Prompt evaluation (Golden Dataset — 20 offers)
python -m tests.eval_dataset.eval_prompts
python -m tests.eval_dataset.eval_prompts --verbose
python -m tests.eval_dataset.eval_prompts --threshold 0.90
```

**Metrics (latest run):**

| Filter             | Precision | Recall | F1    |
| ------------------ | --------- | ------ | ----- |
| No-Phone Guarantee | **100%**  | 100%   | 100%  |
| Async-Friendly     | **100%**  | 90%    | 94.7% |
| Salary Disclosed   | **100%**  | 100%   | 100%  |

---

## 💰 Costs

Everything runs on free tiers:

| Service                 | Free tier limit        | Usage      |
| ----------------------- | ---------------------- | ---------- |
| GitHub Actions          | 2000 min/month         | ~5 min/day |
| Supabase (database)     | 500 MB, 2 GB transfer  | <10 MB     |
| Supabase Edge Functions | 500k invocations/month | ~30/day    |
| Google Gemini           | 15 RPM, 500–1500 RPD   | ~31/day    |
| Resend                  | 3000 emails/month      | 1/day      |
| GitHub Pages            | unlimited              | —          |

**Monthly cost: $0.00 USD.**

---

## 📄 License

MIT — use it, modify it, sell it. Code provided without warranty.

---

<div align="center">

**Built with ❤️ using free tools**

</div>
