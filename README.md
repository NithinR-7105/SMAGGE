# SMAGGE — Sovereign Multi-Agent Growth & Governance Engine

> An autonomous multi-agent system that discovers hyper-targeted business leads and generates secure, compliant, personalised outreach — powered by local LLMs, CrewAI, and a custom AI security layer.

---

## What This Project Demonstrates

| Skill Area | Implementation |
|---|---|
| **Multi-Agent Orchestration** | CrewAI sequential pipeline — Scout → Analyst → Writer → Guard |
| **Local LLM Deployment** | Ollama + llama3.2 (tool-calling capable, fully offline) |
| **AI Security & Governance** | Custom 4-layer security scorer (PII · Injection · Hallucination · Tone) |
| **Feedback Loop** | Rejected messages feed back into the Writer agent context |
| **Workflow Automation** | n8n webhook + daily cron trigger via FastAPI |
| **Full-Stack AI Engineering** | FastAPI REST API + live HTML/JS dashboard |
| **Containerisation** | Docker Compose — PostgreSQL + n8n |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SMAGGE Pipeline                         │
│                                                                  │
│   ┌─────────┐    ┌──────────┐    ┌────────┐    ┌───────────┐   │
│   │  Scout  │───▶│ Analyst  │───▶│ Writer │───▶│  Security │   │
│   │  Agent  │    │  Agent   │    │ Agent  │    │   Guard   │   │
│   └─────────┘    └──────────┘    └────────┘    └─────┬─────┘   │
│   Discovers       Enriches        Drafts         4-layer check  │
│   leads via       each lead       personalised   PII·Inj·Hal    │
│   CSV/Apollo      with OCR        outreach       ·Tone scoring  │
│   /Hunter         + reasoning     (<150 words)         │        │
│                                                         ▼        │
│                              ┌──────────────────────────────┐   │
│                              │      PostgreSQL Database      │   │
│                              │  leads · analyses · outreach  │   │
│                              │       pipeline_runs           │   │
│                              └──────────────┬───────────────┘   │
└─────────────────────────────────────────────┼───────────────────┘
                                              │
              ┌───────────────────────────────┼────────────────┐
              │                               │                │
        ┌─────▼─────┐                  ┌──────▼──────┐  ┌─────▼────┐
        │  FastAPI  │                  │  Dashboard  │  │   n8n    │
        │  REST API │                  │  (HTML/JS)  │  │ Workflow │
        │  :8000    │                  │   :8000/    │  │  :5678   │
        └───────────┘                  │  dashboard  │  └──────────┘
                                       └─────────────┘
```

---

## Project Structure

```
SMAGGE/
├── agents/
│   ├── scout.py          # Lead discovery agent (mock / Apollo / Hunter)
│   ├── analyst.py        # Lead enrichment agent (OCR + reasoning)
│   └── writer.py         # Personalised outreach drafting agent
├── tools/
│   ├── lead_scraper.py   # CrewAI BaseTool — CSV / API lead fetching
│   └── ocr_tool.py       # CrewAI BaseTool — Tesseract OCR
├── tasks/
│   └── pipeline_tasks.py # CrewAI task definitions with context chaining
├── security/
│   ├── guard.py          # SecurityGuard — orchestrates all checks
│   ├── scorer.py         # SecurityScorer — returns SecurityReport
│   ├── checks/
│   │   ├── pii_check.py          # Regex PII detection (40 pts)
│   │   ├── injection_check.py    # Regex + LLM semantic injection check (30 pts)
│   │   ├── hallucination_check.py# LLM cross-reference check (20 pts)
│   │   └── tone_check.py         # LLM tone appropriateness (10 pts)
│   └── guardrails/
│       ├── config.yml    # NeMo Guardrails config (portfolio documentation)
│       └── main.co       # NeMo Guardrails colang rules
├── feedback/
│   └── loop.py           # FeedbackLoop — rejected messages → Writer context
├── api/
│   └── server.py         # FastAPI server — /run /status /leads /runs /approve
├── static/
│   └── dashboard.html    # Live dashboard — 4 pages, full navigation
├── database/
│   └── init.sql          # PostgreSQL schema
├── data/
│   └── mock_leads.csv    # 10 sample SaaS leads
├── n8n/
│   └── smagge_workflow.json  # Importable n8n workflow
├── crew.py               # Main pipeline entry point
├── docker-compose.yml    # PostgreSQL + n8n containers
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variable template
```

---

## Quick Start

### Prerequisites
- Python 3.12
- Docker Desktop
- [Ollama](https://ollama.ai) with `llama3.2` pulled
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Windows)

### 1. Clone & set up environment
```bash
git clone https://github.com/nithin/smagge.git
cd smagge

py -3.12 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure environment
```bash
copy .env.example .env
# Edit .env with your settings
```

### 3. Start infrastructure
```bash
docker-compose up -d         # PostgreSQL + n8n
ollama pull llama3.2         # Download local LLM
```

### 4. Run the pipeline (Terminal 1)
```bash
python crew.py
```

### 5. Start the API server (Terminal 2)
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Open the dashboard
```
http://localhost:8000/dashboard
```

---

## The 4-Phase Build

### Phase 1 — Multi-Agent Pipeline
Three CrewAI agents running sequentially on a local LLM:
- **Scout** uses `LeadScraperTool` to fetch leads from mock CSV, Apollo, or Hunter.io
- **Analyst** enriches each lead with `OCRTool` (Tesseract) + LLM reasoning
- **Writer** drafts a personalised outreach email per lead (under 150 words)

### Phase 2 — Security Guard Layer
A custom 4-layer security scorer intercepts every Writer output before it reaches the database:

| Check | Points | Method |
|---|---|---|
| PII Detection | 40 | Regex patterns (email, phone, SSN, credit card) |
| Prompt Injection | 30 | Regex + Ollama LLM semantic check |
| Hallucination | 20 | LLM cross-references message facts vs source data |
| Tone | 10 | LLM appropriateness assessment |

Messages scoring below 70/100 are automatically rejected and logged.

The `security/guardrails/` folder documents how this maps to a [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) integration pattern (C++ build tools required on Windows — implemented natively instead).

### Phase 3 — Automation & Feedback Loop
- **FastAPI server** exposes `/run`, `/status`, `/leads`, `/runs`, `/approve` endpoints
- **n8n workflow** triggers the pipeline on a daily 9AM schedule (Mon–Fri) and via webhook
- **Feedback loop** queries previously rejected messages from PostgreSQL and injects them into the Writer agent's context so it learns from past mistakes

### Phase 4 — Dashboard & Portfolio
- Live HTML/JS dashboard served via FastAPI at `/dashboard`
- 4 working pages: Dashboard, Leads, Security Logs, Settings
- Approve / Reject buttons feed back into the pipeline via `/approve`
- Settings page includes a "Run Pipeline Now" button
- Auto-refreshes every 30 seconds; falls back to mock data when API is offline

---

## Environment Variables

```env
# LLM
OLLAMA_MODEL=llama3.2

# Lead Source: mock | apollo | hunter
LEAD_SOURCE=mock

# Apollo (optional)
APOLLO_API_KEY=your_key_here

# Hunter.io (optional)
HUNTER_API_KEY=your_key_here

# Targeting
TARGET_INDUSTRY=SaaS
TARGET_JOB_TITLE=Head of Growth
TARGET_LOCATION=United States

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=smagge_db
POSTGRES_USER=smagge
POSTGRES_PASSWORD=smagge_secret

# Tesseract (Windows)
TESSERACT_PATH=C:\Program Files\Tesseract-OCR
```

---

## Security Score Breakdown

```
100 pts total
├── PII Check         (40 pts) — HARD FAIL if any PII detected
├── Injection Check   (30 pts) — Regex layer + LLM semantic layer
├── Hallucination     (20 pts) — LLM fact cross-reference
└── Tone              (10 pts) — LLM appropriateness check

≥ 70 pts → Approved ✓
< 70 pts → Rejected ✗ (logged with reason, fed back to Writer)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | [CrewAI](https://crewai.com) 1.x |
| Local LLM | [Ollama](https://ollama.ai) + llama3.2 |
| OCR | Tesseract + pytesseract + OpenCV |
| Database | PostgreSQL 15 (Docker) |
| ORM | SQLAlchemy + psycopg2 |
| API | FastAPI + Uvicorn |
| Workflow Automation | n8n (Docker) |
| Frontend | Vanilla HTML/JS + Tailwind CSS + Material Symbols |
| Containerisation | Docker Compose |
| Security | Custom Python layer + NeMo Guardrails pattern |

---

## Roadmap

- [ ] Apollo & Hunter.io live API integration
- [ ] Email sending via SendGrid / Gmail API
- [ ] Multi-tenant support
- [ ] Slack notification on pipeline completion
- [ ] Fine-tuned local model for outreach quality

---

*Built by Nithin · Portfolio project showcasing autonomous multi-agent AI systems*
