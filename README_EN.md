# Live Observatory v6

> 🌐 **Spanish version available**: [README.md](README.md)

> Real-time trend detection dashboard with SQLite, FastAPI, and outbreak detection algorithm

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-orange.svg)](https://sqlite.org/)

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd observatorio_v6_backend

# Run with automatic script
./run.sh
```

The dashboard will be available at: **http://127.0.0.1:8765**

---

## 📋 System Requirements

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows with WSL
- **Disk Space**: ~100 MB minimum
- **RAM**: 512 MB minimum

---

## **Project Structure**

```
observatorio_v6_backend/
├── app.py                 # FastAPI backend (main endpoints)
├── modules/               # Separated modules
│   ├── __init__.py
│   ├── database.py        # SQLite connection + migrations
│   └── models.py          # Pydantic models
├── test_core.py           # Unit tests (pytest)
├── frontend/
│   └── index.html         # Vanilla JS SPA, CSS-in-HTML
├── data/
│   └── observatorio.db    # SQLite database (persistent)
│   └── observatorio.log   # Structured logs
├── doc/                   # Technical documentation
│   ├── app.md            # Backend documentation
│   ├── frontend.md       # Frontend documentation
│   ├── database.md       # Schema and queries
│   ├── api_reference.md  # API reference
│   ├── run_sh.md         # Startup script guide
│   ├── requirements.md   # Dependencies
│   ├── README.md         # Spanish documentation
│   └── README_EN.md      # This file (English)
│   ├── modules.md        # Modularization details
├── requirements.txt       # Python dependencies
├── run.sh                 # Auto-startup script
├── README.md              # Spanish README
└── README_EN.md           # English README (this file)
├── requirements.txt       ← Python dependencies
├── run.sh                 ← Auto-start script
├── README.md              ← Spanish README
└── README_EN.md           ← English README (this file)
```

---

## 🌟 Key Features

### Trend Detection
- **Hot Topics**: Terms ranked by accumulated score
- **Outbreak Detection**: Visual ranking by emergency + specificity + delta
- **Signal Traceability**: "View Origin" modal showing evidence from `term_hits`
- **Multi-source**: Wikipedia, Google Trends, Reddit, Mastodon, Hacker News

### Dashboard Tabs
- **Radar**: Real-time dashboard with KPIs
- **Outbreaks**: Outbreak table with visual ranking
- **Observation**: Low-confidence signal tray
- **History**: Sample browser with detail view
- **Watchlist**: Tracked terms with alerts
- **Config**: Telegram bot configuration
- **Report**: TXT report generation

### Alert System
- 3-tier system: Detected → Observed → Alerted
- Telegram integration (optional)
- Cooldown system to avoid spam
- Specificity scoring (phrase vs. single word)

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard interface |
| `/api/state` | GET | System state and KPIs |
| `/api/terms` | GET | Aggregated term ranking |
| `/api/outbreaks` | GET | Outbreak detection with visual ranking |
| `/api/signal-origin/{term}` | GET | **Signal traceability** |
| `/api/run` | POST | Trigger data collection run |
| `/api/health` | GET | Health check |

See [doc/api_reference.md](doc/api_reference.md) for complete API documentation.

---

## 📊 Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `runs` | Data collection executions |
| `samples` | Raw data from each source |
| `term_hits` | Term appearances with title/source/score |
| `outbreaks` | Detected outbreaks with metadata |
| `alerts` | Historical alert log |
| `watchlist` | Tracked terms |
| `aliases` | Term canonicalization |

See [doc/database.md](doc/database.md) for full schema and queries.

---

## 🎨 Customization

### Change Detection Threshold
```python
# In app.py or via /api/settings
OUTBREAK_THRESHOLD = 45.0  # Default emergency threshold
```

### Add New Data Source
1. Create collector function in `app.py`
2. Add to `collect_all()` dispatcher
3. Document in [doc/app.md](doc/app.md)

See [doc/app.md - Section 6](doc/app.md#6-data-collectors) for details.

### Modify Theme
- Edit CSS variables in `frontend/index.html` (lines 11-15)
- Three built-in themes: default, cyber, light
- Three font options: monospace, modern, minimal

See [doc/frontend.md](doc/frontend.md) for styling guide.

---

## 📱 Telegram Integration

Configure in **Config** tab:

```
Bot Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
Chat ID: -1001234567890
```

Or via API:
```bash
curl -X POST http://127.0.0.1:8765/api/settings \
  -H "Content-Type: application/json" \
  -d '{"telegram_enabled": true, "telegram_bot_token": "...", "telegram_chat_id": "..."}'
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8765 in use | Change in `run.sh` or kill existing process |
| Database locked | WAL mode handles concurrency; restart if stuck |
| Empty dashboard | Run `/api/run` to collect initial data |
| Telegram not working | Verify bot token and chat ID format |

See [doc/run_sh.md - Troubleshooting](doc/run_sh.md#troubleshooting) for more.

---

## 📚 Documentation Index

- **[doc/README_EN.md](doc/README_EN.md)** ← Documentation guide (this file)
- **[doc/app.md](doc/app.md)** ← Backend architecture and algorithms
- **[doc/frontend.md](doc/frontend.md)** ← Frontend structure and JS
- **[doc/database.md](doc/database.md)** ← SQLite schema and queries
- **[doc/api_reference.md](doc/api_reference.md)** ← Complete API docs
- **[doc/run_sh.md](doc/run_sh.md)** ← Startup script details
- **[doc/requirements.md](doc/requirements.md)** ← Dependencies explained

---

## 📝 Version History

| Version | Key Features |
|---------|-------------|
| v6.0.0 | Initial release with core detection |
| v6.1.0 | Added visual ranking by specificity |
| v6.1.2 | Improved component suppression, cooldown fixes |
| **v6.1.3** | **Strict signal traceability from term_hits** |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit Pull Request

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 💬 Support

- **Issues**: Create GitHub issue for bugs
- **Questions**: Use Discussions for Q&A
- **Email**: contact@example.com

---

<p align="center">
  <b>Live Observatory v6.1.3</b><br>
  <i>Real-time trend detection with traceability</i>
</p>
