# HealthIQ

**AI-powered healthcare analytics platform** — six autonomous agents operating on FHIR R4 patient data to deliver real-time risk scoring, clinical NLP, operational intelligence, and proactive alerting.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Dashboard                          │
│              (Patient list · Risk heatmap · Alerts)             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     FastAPI  (Python 3.11)                       │
│          /patients  /encounters  /alerts  /risk-scores           │
└──┬──────────────────────────────────────────────┬───────────────┘
   │ SQLAlchemy                                   │ LangGraph
   │                                              │
┌──▼──────────────┐              ┌────────────────▼───────────────┐
│   PostgreSQL 16 │              │        Agent Orchestrator       │
│                 │              │  ┌─────────────────────────┐   │
│  patients       │◄─────────────┤  │  1. Ingestion Agent     │   │
│  encounters     │              │  │  2. Risk Scoring Agent  │   │
│  observations   │◄─────────────┤  │  3. NLP Agent           │   │
│  risk_scores    │◄─────────────┤  │  4. Operations Agent    │   │
│  alerts         │◄─────────────┤  │  5. Alert Agent         │   │
└─────────────────┘              │  │  6. Reporting Agent     │   │
                                 │  └─────────────────────────┘   │
                                 └────────────────────────────────┘
```

### Agents

| # | Agent | Responsibility |
|---|-------|---------------|
| 1 | **Ingestion** | Polls FHIR R4 server, normalises resources, persists to Postgres |
| 2 | **Risk Scoring** | XGBoost models for readmission, sepsis, deterioration risk |
| 3 | **NLP** | Claude-powered extraction of diagnoses, medications, care gaps from notes |
| 4 | **Operations** | Bed utilisation, ED throughput, staffing anomaly detection |
| 5 | **Alert** | Threshold-based and ML-triggered alerts with severity routing |
| 6 | **Reporting** | Automated PDF/CSV population health reports via scheduled triggers |

---

## Getting Started

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- Python 3.11+ (for local development outside Docker)
- An Anthropic API key

### 1. Clone & configure

```bash
git clone <repo-url>
cd healthiq
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum
```

### 2. Start services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL 16** on `localhost:5432` — schema auto-applied via `infra/migrations/init.sql`
- **HealthIQ API** on `http://localhost:8000`

### 3. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","timestamp":"...","version":"0.1.0","services":{"database":{"status":"ok",...}}}
```

Interactive docs: http://localhost:8000/docs

### 4. Local development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL to a local Postgres instance
uvicorn api.main:app --reload
```

### 5. Run tests

```bash
pip install pytest httpx
pytest tests/
```

---

## Project Structure

```
healthiq/
├── agents/             # Six autonomous AI agents (LangGraph)
│   ├── ingestion/
│   ├── risk_scoring/
│   ├── nlp/
│   ├── operations/
│   ├── alert/
│   └── reporting/
├── api/                # FastAPI application
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/         # SQLAlchemy ORM models
│   ├── routers/        # Route handlers
│   └── services/       # Business logic
├── analytics/          # Shared analytics utilities
├── dashboard/          # React frontend (Day 3+)
├── infra/
│   ├── docker/         # Dockerfile
│   └── migrations/     # init.sql — PostgreSQL schema
├── tests/
├── docs/
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Roadmap

- **Day 1** — Project scaffold, schema, health endpoint ✅
- **Day 2** — Ingestion Agent + FHIR R4 data pipeline
- **Day 3** — Risk Scoring Agent (XGBoost) + model serving
- **Day 4** — NLP Agent (Claude) + clinical note extraction
- **Day 5** — Alert Agent + React dashboard foundations
- **Day 6** — Operations & Reporting agents + full integration

---

## License

Private — HealthIQ internal project.
