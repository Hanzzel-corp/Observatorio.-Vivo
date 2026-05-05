# Live Observatory v6 Documentation

> 🌐 **Spanish version available**: [README.md](README.md)

## File Index

This `doc/` folder contains detailed documentation for each system component:

| File | Description |
|------|-------------|
| [`app.md`](app.md) | FastAPI backend (endpoints and main logic) |
| [`modules.md`](modules.md) | Separated modules (database, models) |
| [`frontend.md`](frontend.md) | Vanilla JavaScript SPA interface |
| [`database.md`](database.md) | SQLite schema and SQL queries |
| [`api_reference.md`](api_reference.md) | Complete REST API documentation |
| [`run_sh.md`](run_sh.md) | Auto-startup script guide |
| [`requirements.md`](requirements.md) | Python dependencies |
| [`README.md`](README.md) | Spanish documentation |
| [`README_EN.md`](README_EN.md) | This file (English) |

---

## Project Structure

```
observatorio_v6_backend/
├── app.py                 ← [See app.md](app.md) - FastAPI endpoints
├── modules/               ← [See modules.md](modules.md)
│   ├── __init__.py
│   ├── database.py        ← SQLite connection + migrations
│   └── models.py          ← Pydantic models
├── test_core.py           ← Unit tests (pytest)
├── frontend/
│   └── index.html         ← [See frontend.md](frontend.md)
├── data/
│   └── observatorio.db    ← [See database.md](database.md)
├── doc/
│   ├── app.md
│   ├── modules.md         ← NEW: Modules documentation
│   ├── frontend.md
│   ├── database.md
│   ├── api_reference.md
│   ├── run_sh.md
│   ├── requirements.md
│   ├── README.md          ← Spanish index
│   └── README_EN.md       ← This file (English index)
├── requirements.txt       ← [See requirements.md](requirements.md)
├── run.sh                 ← [See run_sh.md](run_sh.md)
├── README.md              ← Spanish main README
└── README_EN.md           ← English main README
```

---

## How to Use This Documentation

### To Understand the Backend

1. Read [`app.md`](app.md) - Explains `app.py` structure section by section:
   - Constants and configuration
   - Database and schema
   - Data collectors
   - Outbreak detection algorithm
   - FastAPI endpoints
   - Signal traceability (`/api/signal-origin/{term}`)

### To Modify the Interface

1. Read [`frontend.md`](frontend.md) - Documents:
   - CSS variables and visual themes
   - Structure of the 6 dashboard tabs
   - JavaScript and state management
   - Communication with backend

### To Work with Data

1. Read [`database.md`](database.md) - Includes:
   - Complete schema of 7 tables
   - Indexes and optimization
   - SQL analysis queries
   - Useful query examples

### To Integrate with Other Systems

1. Read [`api_reference.md`](api_reference.md) - Provides:
   - All 17+ endpoints documented
   - Examples in bash, Python, and JavaScript
   - Error codes
   - Request/response formats

### To Deploy or Maintain

1. Read [`run_sh.md`](run_sh.md) - Explains:
   - How the startup script works
   - Virtual environment creation
   - Common troubleshooting

2. Read [`requirements.md`](requirements.md) - Details:
   - Each dependency and its purpose
   - Dependency tree
   - Versions and compatibility

---

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│  (Web Browser)                                                    │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    frontend/index.html                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Radar     │  │  Outbreaks  │  │   History   │             │
│  │  (Dashboard)│  │  (Detector) │  │  (Samples)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Watchlist  │  │   Config    │  │   Report    │             │
│  │  (Tracking) │  │  (Telegram) │  │   (TXT)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                      ↑ JavaScript (fetch API)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py (FastAPI)                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │    /api/run     │───▶│   Collectors    │───▶│  SQLite DB  │  │
│  │  (POST)         │    │   (async)       │    │  (WAL mode) │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
│         ↑                    │  • Wikipedia                     │
│         │                    │  • Google Trends                 │
│  ┌──────┴───────────────────┤  • Reddit                        │
│  │    API REST (17+ endpoints) • Mastodon                     │
│  │                           │  • Hacker News                  │
│  │  • /api/state             │                                  │
│  │  • /api/terms             │                                  │
│  │  • /api/outbreaks         │                                  │
│  │  • /api/signal-origin/*   │  ← Signal traceability           │
│  │  • /api/alerts            │                                  │
│  │  • /api/watchlist         │                                  │
│  │  • /api/export/*          │                                  │
│  │                           │                                  │
│  │  Outbreak Detector ◄──────┘                                  │
│  │  (Scoring algorithm)                                         │
│  │                                                              │
│  └──────────────────────────────────────────────────────────────┘
                       │
                       ▼ (optional)
              ┌─────────────────┐
              │   Telegram API  │
              │  (push alerts)  │
              └─────────────────┘
```

---

## Glossary of Terms

| Term | Definition |
|------|------------|
| **Run** | Complete execution capturing data from all sources |
| **Sample** | Data captured from a specific source in a run |
| **Hit** | Term appearance in a processed title |
| **Score** | Weighted score based on source and position |
| **Emergency** | Outbreak detector composite metric (0-150) |
| **Delta** | Score difference between latest run and previous |
| **Bucket** | Geographic classification: "es" (Hispanic) or "intl" (International) |
| **Canonical** | Normalized term form (after applying aliases) |
| **WAL** | Write-Ahead Logging (SQLite concurrency mode) |
| **Visual Primary** | Term displayed in dashboard (not suppressed) |
| **Specificity Score** | Bonus for multi-word phrases vs. single words |

---

## Quick Links

### By Task

| I want to... | Documentation |
|--------------|---------------|
| Understand outbreak algorithm | [app.md - Section 9](app.md#9-outbreak-detection-algorithm) |
| Modify visual theme | [frontend.md - CSS Styles](frontend.md#css-styles-lines-10-20) |
| Add new data source | [app.md - Collectors](app.md#6-data-collectors-lines-319-446) |
| Query data directly | [database.md - Queries](database.md#analysis-queries) |
| Integrate with my app | [api_reference.md](api_reference.md) |
| Fix startup issues | [run_sh.md - Troubleshooting](run_sh.md#troubleshooting) |
| Understand signal traceability | [app.md - Section 10](app.md#10-signal-traceability) |

### By Component

| Component | Main File | Documentation |
|-----------|-----------|---------------|
| Backend | `app.py` | [app.md](app.md) |
| Modules | `modules/` | [modules.md](modules.md) |
| Frontend | `frontend/index.html` | [frontend.md](frontend.md) |
| Database | `data/observatorio.db` | [database.md](database.md) |
| REST API | Endpoints in `app.py` | [api_reference.md](api_reference.md) |
| Startup Script | `run.sh` | [run_sh.md](run_sh.md) |
| Dependencies | `requirements.txt` | [requirements.md](requirements.md) |
| Tests | `test_core.py` | - |

---

## Updates

To keep this documentation current after code changes:

1. **If you modify `app.py`**: Update [app.md](app.md)
2. **If you modify `modules/`**: Update [modules.md](modules.md)
3. **If you modify `frontend/index.html`**: Update [frontend.md](frontend.md)
4. **If you add endpoints**: Update [api_reference.md](api_reference.md)
5. **If you change SQL schema**: Update [database.md](database.md)
6. **If you change dependencies**: Update [requirements.md](requirements.md)

---

## File: `doc/README_EN.md`
- **Purpose**: English documentation index and navigation guide
- **Referenced files**: 7 technical documents + translations
- **Target audience**: Developers and advanced users

---

<p align="center">
  <b>Live Observatory v6.1.3 Documentation</b><br>
  <i>Real-time trend detection with strict traceability</i>
</p>
