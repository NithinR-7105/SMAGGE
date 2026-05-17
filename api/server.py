"""
SMAGGE FastAPI Server — Phase 3
--------------------------------
Exposes the pipeline as an HTTP API so n8n can trigger it via webhook.

Endpoints:
  POST /run        — trigger a full pipeline run
  GET  /status     — check server health
  GET  /runs       — list recent pipeline runs from DB
  POST /approve    — approve/reject a specific outreach message (feedback loop)

Run:
  uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

n8n webhook triggers this server at: http://localhost:8000/run
"""

import os
import json
import psycopg2
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

load_dotenv()

app = FastAPI(
    title="SMAGGE API",
    description="Sovereign Multi-Agent Growth & Governance Engine",
    version="1.0.0",
)

# Allow n8n (localhost:5678) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the HTML dashboard at /dashboard
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    """Open the Growth Engine dashboard in your browser."""
    return FileResponse(os.path.join(_static_dir, "dashboard.html"))

@app.get("/architecture", include_in_schema=False)
def serve_architecture():
    """Open the system architecture diagram in your browser."""
    return FileResponse(os.path.join(_static_dir, "architecture.html"))


# ─── Request / Response Models ────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    industry:  str = "SaaS"
    job_title: str = "Head of Growth"
    location:  str = "United States"
    limit:     int = 5
    trigger:   str = "n8n_webhook"


class ApprovalRequest(BaseModel):
    outreach_id: int
    approved:    bool
    reason:      Optional[str] = ""


# ─── DB Helper ────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST",     "localhost"),
        port=int(os.getenv("POSTGRES_PORT",  5432)),
        dbname=os.getenv("POSTGRES_DB",      "smagge_db"),
        user=os.getenv("POSTGRES_USER",      "smagge"),
        password=os.getenv("POSTGRES_PASSWORD", "smagge_secret"),
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/status")
def health_check():
    """n8n uses this to verify the server is alive before triggering a run."""
    return {
        "status":    "ok",
        "service":   "SMAGGE",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/run")
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Triggers a full Scout → Analyst → Writer → Security Guard pipeline run.
    Called by n8n via webhook or timer.
    Returns immediately with run metadata; pipeline runs in background.
    """
    logger.info(f"Pipeline triggered via API | trigger={request.trigger}")

    # Import here to avoid circular imports
    from crew import run_pipeline as execute_pipeline

    # Run in background so n8n doesn't time out waiting
    background_tasks.add_task(
        execute_pipeline,
        industry=request.industry,
        job_title=request.job_title,
        location=request.location,
        limit=request.limit,
        trigger=request.trigger,
    )

    return {
        "status":    "started",
        "message":   f"Pipeline triggered for {request.industry} / {request.job_title}",
        "trigger":   request.trigger,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/runs")
def list_runs(limit: int = 10):
    """Returns recent pipeline run history from the database."""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, status, leads_found, leads_processed,
                   trigger_source, started_at, completed_at
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT %s
        """, (limit,))

        columns = ["id", "status", "leads_found", "leads_processed",
                   "trigger_source", "started_at", "completed_at"]
        runs = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Convert datetimes to strings
        for run in runs:
            for key in ["started_at", "completed_at"]:
                if run[key]:
                    run[key] = run[key].isoformat()

        cur.close()
        conn.close()
        return {"runs": runs, "total": len(runs)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads")
def list_leads(status: str = None, limit: int = 20):
    """Returns leads with their outreach status and security scores."""
    try:
        conn = get_db()
        cur  = conn.cursor()

        query = """
            SELECT l.full_name, l.job_title, l.company, l.industry,
                   o.subject_line, o.status, o.security_score, o.rejection_reason,
                   o.created_at
            FROM leads l
            JOIN outreach o ON l.id = o.lead_id
        """
        params = []
        if status:
            query += " WHERE o.status = %s"
            params.append(status)
        query += " ORDER BY o.created_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        columns = ["full_name", "job_title", "company", "industry",
                   "subject_line", "status", "security_score",
                   "rejection_reason", "created_at"]
        leads = [dict(zip(columns, row)) for row in cur.fetchall()]

        for lead in leads:
            if lead.get("created_at"):
                lead["created_at"] = lead["created_at"].isoformat()

        cur.close()
        conn.close()
        return {"leads": leads, "total": len(leads)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve")
def approve_outreach(request: ApprovalRequest):
    """
    Human approve/reject endpoint — called from the Phase 4 dashboard.
    Updates outreach status and feeds rejection reason into the feedback loop.
    """
    try:
        from feedback import FeedbackLoop
        loop = FeedbackLoop()
        loop.log_approval_decision(
            outreach_id=request.outreach_id,
            approved=request.approved,
            reason=request.reason,
        )

        return {
            "status":      "updated",
            "outreach_id": request.outreach_id,
            "approved":    request.approved,
            "timestamp":   datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
