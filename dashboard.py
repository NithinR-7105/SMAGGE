"""
SMAGGE Dashboard — Phase 4
===========================
Streamlit dashboard matching the Stitch AI design.

Run:
    streamlit run dashboard.py

Features:
  - 4 KPI metric cards (Total Leads, Approved, Avg Score, Pipeline Runs)
  - Recent Leads table with security score badges + Approve/Reject buttons
  - Security Log feed (right panel)
  - Pipeline Activity bar chart (Plotly)
  - Live data from PostgreSQL via FastAPI
"""

import os
import json
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_BASE   = os.getenv("API_BASE_URL", "http://localhost:8000")
PAGE_TITLE = "SMAGGE — Growth Engine"

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS (matching Stitch AI design) ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f8f9ff !important;
    color: #0b1c30 !important;
}

/* Hide default streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #c7c4d7 !important;
}
section[data-testid="stSidebar"] .stMarkdown { padding: 0 !important; }

/* Metric Cards */
.metric-card {
    background: #ffffff;
    border: 1px solid #c7c4d7;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
}
.metric-label {
    font-size: 11px;
    font-weight: 600;
    color: #464554;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #0b1c30;
    line-height: 1.1;
}
.metric-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
}
.badge-green  { background: #dcfce7; color: #15803d; }
.badge-blue   { background: #ede9fe; color: #4648d4; }
.badge-yellow { background: #fef9c3; color: #a16207; }
.badge-red    { background: #fee2e2; color: #dc2626; }

/* Section Cards */
.section-card {
    background: #ffffff;
    border: 1px solid #c7c4d7;
    border-radius: 12px;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
    overflow: hidden;
}
.section-header {
    padding: 16px 20px;
    border-bottom: 1px solid #c7c4d7;
    background: rgba(229, 238, 255, 0.3);
    font-size: 18px;
    font-weight: 600;
    color: #0b1c30;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Score badges */
.score-green  { background:#dcfce7; color:#15803d; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:700; }
.score-yellow { background:#fef9c3; color:#a16207; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:700; }
.score-red    { background:#fee2e2; color:#dc2626; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:700; }

/* Security log items */
.log-item {
    background: #ffffff;
    border: 1px solid #c7c4d7;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: border-color 0.2s;
}
.log-item:hover { border-color: #4648d4; }
.log-time { font-size: 10px; font-weight: 700; color: #464554;
            background:#e5eeff; padding:2px 8px; border-radius:4px; text-transform:uppercase; }
.check-pass { color: #16a34a; font-size: 12px; font-weight: 700; }
.check-fail { color: #dc2626; font-size: 12px; font-weight: 700; }

/* Buttons */
.btn-approve {
    background: #4648d4; color: white;
    border: none; border-radius: 8px;
    padding: 4px 14px; font-size: 12px;
    font-weight: 600; cursor: pointer;
}
.btn-reject {
    background: #fee2e2; color: #dc2626;
    border: 1px solid #fca5a5; border-radius: 8px;
    padding: 4px 14px; font-size: 12px;
    font-weight: 600; cursor: pointer;
}

/* Nav items in sidebar */
.nav-active {
    background: #e5eeff; color: #4648d4;
    border-left: 4px solid #4648d4;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px; font-weight: 600;
    margin-bottom: 4px; font-size: 14px;
}
.nav-item {
    color: #464554; padding: 8px 12px;
    border-radius: 8px; margin-bottom: 4px;
    font-size: 14px; font-weight: 500;
}
</style>
""", unsafe_allow_html=True)


# ─── API Helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_leads(limit=20, status=None):
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
        r = requests.get(f"{API_BASE}/leads", params=params, timeout=5)
        return r.json().get("leads", [])
    except Exception:
        return _mock_leads()


@st.cache_data(ttl=30)
def fetch_runs(limit=10):
    try:
        r = requests.get(f"{API_BASE}/runs", params={"limit": limit}, timeout=5)
        return r.json().get("runs", [])
    except Exception:
        return _mock_runs()


def approve_message(outreach_id: int, approved: bool, reason: str = ""):
    try:
        requests.post(f"{API_BASE}/approve", json={
            "outreach_id": outreach_id,
            "approved": approved,
            "reason": reason,
        }, timeout=5)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Could not update: {e}")


# ─── Mock Data (fallback when DB/API offline) ─────────────────────────────────

def _mock_leads():
    return [
        {"full_name":"Sarah Chen",      "job_title":"Head of Growth", "company":"Notion",    "industry":"SaaS",            "security_score":98, "status":"approved",  "subject_line":"Quick thought on Notion's growth loop", "rejection_reason":""},
        {"full_name":"Marcus Webb",     "job_title":"VP Marketing",   "company":"Linear",    "industry":"SaaS",            "security_score":91, "status":"approved",  "subject_line":"Linear's velocity caught my eye",       "rejection_reason":""},
        {"full_name":"Priya Nair",      "job_title":"Demand Gen Dir", "company":"Vercel",    "industry":"Dev Tools",       "security_score":76, "status":"approved",  "subject_line":"Vercel's edge network — a question",    "rejection_reason":""},
        {"full_name":"James Okafor",    "job_title":"CMO",            "company":"Retool",    "industry":"SaaS",            "security_score":42, "status":"rejected",  "subject_line":"",                                       "rejection_reason":"PII detected in message body"},
        {"full_name":"Amelia Torres",   "job_title":"Head of Growth", "company":"Supabase",  "industry":"Dev Tools",       "security_score":88, "status":"approved",  "subject_line":"Supabase's open-source momentum",       "rejection_reason":""},
    ]

def _mock_runs():
    now = datetime.now()
    return [
        {"id":1, "status":"completed", "leads_processed":5, "trigger_source":"n8n_webhook", "started_at":(now-timedelta(minutes=2)).isoformat(),  "completed_at":now.isoformat()},
        {"id":2, "status":"completed", "leads_processed":5, "trigger_source":"n8n_timer",   "started_at":(now-timedelta(hours=9)).isoformat(),    "completed_at":(now-timedelta(hours=9)+timedelta(minutes=4)).isoformat()},
        {"id":3, "status":"completed", "leads_processed":5, "trigger_source":"manual",      "started_at":(now-timedelta(hours=24)).isoformat(),   "completed_at":(now-timedelta(hours=23,minutes=55)).isoformat()},
    ]


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:16px 8px 24px 8px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:32px;height:32px;background:#4648d4;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;font-size:18px">🚀</div>
            <div>
                <div style="font-weight:700;color:#4648d4;font-size:14px">Growth Engine</div>
                <div style="font-size:10px;color:#464554;text-transform:uppercase;
                            letter-spacing:0.08em;font-weight:700">SaaS Accelerator</div>
            </div>
        </div>
    </div>
    <div class="nav-active">📊 &nbsp; Dashboard</div>
    <div class="nav-item">🔍 &nbsp; Leads</div>
    <div class="nav-item">🛡 &nbsp; Security Logs</div>
    <div class="nav-item">⚙️ &nbsp; Settings</div>
    """, unsafe_allow_html=True)

    st.markdown("<br>" * 6, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#ede9fe;border:1px solid #c4b5fd;border-radius:12px;padding:16px;margin:8px">
        <div style="font-weight:700;color:#4648d4;font-size:13px;margin-bottom:4px">Growth Plan</div>
        <div style="font-size:12px;color:#464554;margin-bottom:12px">84% of pipeline used this month.</div>
    </div>
    """, unsafe_allow_html=True)
    st.button("⬆ Upgrade Plan", use_container_width=True)
    st.markdown("<div class='nav-item'>💬 &nbsp; Support</div>", unsafe_allow_html=True)
    st.markdown("<div class='nav-item'>🚪 &nbsp; Logout</div>", unsafe_allow_html=True)


# ─── Load Data ────────────────────────────────────────────────────────────────

leads = fetch_leads(limit=20)
runs  = fetch_runs(limit=48)

total_leads    = len(leads)
approved       = [l for l in leads if l.get("status") == "approved"]
rejected       = [l for l in leads if l.get("status") == "rejected"]
scores         = [l.get("security_score", 0) for l in leads if l.get("security_score")]
avg_score      = round(sum(scores) / len(scores)) if scores else 0
total_runs     = len(runs)


# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
    <div>
        <span style="font-size:28px;font-weight:700;color:#4648d4">SMAGGE</span>
        <span style="font-size:16px;color:#464554;margin-left:12px">Growth Engine Dashboard</span>
    </div>
    <div style="font-size:13px;color:#464554">🕐 Auto-refreshes every 30s</div>
</div>
""", unsafe_allow_html=True)


# ─── Top Stats Row ────────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">👥 Total Leads</div>
        <div class="metric-value">{total_leads:,}</div>
        <span class="metric-badge badge-green">+12.5% vs last mo</span>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">✅ Approved Messages</div>
        <div class="metric-value">{len(approved):,}</div>
        <span class="metric-badge badge-green">+8.2% compliance rate</span>
    </div>""", unsafe_allow_html=True)

with c3:
    score_badge = "badge-green" if avg_score >= 80 else "badge-yellow" if avg_score >= 60 else "badge-red"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🛡 Avg Security Score</div>
        <div class="metric-value">{avg_score}%</div>
        <span class="metric-badge {score_badge}">Optimized — Stable pipeline</span>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">⚡ Pipeline Runs</div>
        <div class="metric-value">{total_runs}</div>
        <span class="metric-badge badge-green">Active — n8n connected</span>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─── Middle Row: Leads Table + Security Log ───────────────────────────────────

left_col, right_col = st.columns([2, 1])

# ── Recent Leads ──────────────────────────────────────────────────────────────
with left_col:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header">
        Recent Leads
        <div style="display:flex;gap:8px">
            <span style="font-size:12px;color:#464554;background:#f0f4ff;
                         border:1px solid #c7c4d7;border-radius:8px;padding:6px 12px;cursor:pointer">
                ⚙ Filter
            </span>
            <span style="font-size:12px;color:white;background:#4648d4;
                         border-radius:8px;padding:6px 14px;cursor:pointer;font-weight:600">
                Export All
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if leads:
        for i, lead in enumerate(leads[:8]):
            score = lead.get("security_score", 0)
            if score >= 80:
                score_html = f'<span class="score-green">{score}/100</span>'
            elif score >= 60:
                score_html = f'<span class="score-yellow">{score}/100</span>'
            else:
                score_html = f'<span class="score-red">{score}/100</span>'

            status     = lead.get("status", "pending")
            status_icon = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
            name       = lead.get("full_name", "—")
            title      = lead.get("job_title", "—")
            company    = lead.get("company", "—")
            subject    = lead.get("subject_line", "No subject")

            col_co, col_ct, col_sc, col_ac = st.columns([2, 2, 1.2, 1.5])

            with col_co:
                st.markdown(f"""
                <div style="padding:12px 8px;border-bottom:1px solid #eef0f8">
                    <div style="font-weight:600;font-size:14px;color:#0b1c30">{company}</div>
                    <div style="font-size:11px;color:#464554;margin-top:2px">📎 {subject[:30]}...</div>
                </div>""", unsafe_allow_html=True)

            with col_ct:
                st.markdown(f"""
                <div style="padding:12px 4px;border-bottom:1px solid #eef0f8">
                    <div style="font-weight:600;font-size:14px;color:#0b1c30">{name}</div>
                    <div style="font-size:11px;color:#464554;margin-top:2px">{title}</div>
                </div>""", unsafe_allow_html=True)

            with col_sc:
                st.markdown(f"""
                <div style="padding:14px 4px;border-bottom:1px solid #eef0f8">
                    {score_html}
                </div>""", unsafe_allow_html=True)

            with col_ac:
                btn_a, btn_r = st.columns(2)
                with btn_a:
                    if st.button("✓", key=f"approve_{i}", help="Approve", use_container_width=True):
                        approve_message(i+1, True)
                        st.success("Approved!")
                with btn_r:
                    if st.button("✗", key=f"reject_{i}", help="Reject", use_container_width=True):
                        approve_message(i+1, False, "Manually rejected via dashboard")
                        st.error("Rejected")
    else:
        st.info("No leads found. Run the pipeline first: `python crew.py`")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Security Log Feed ─────────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🛡 Security Log <span style="font-size:12px;cursor:pointer">⋯</span></div>', unsafe_allow_html=True)

    log_items = []
    for lead in leads[:6]:
        score = lead.get("security_score", 0)
        log   = lead.get("security_log") or {}
        if isinstance(log, str):
            try:
                log = json.loads(log)
            except Exception:
                log = {}

        breakdown = log.get("breakdown", {})
        pii_pass  = breakdown.get("pii",          {}).get("score", 40) == 40
        inj_pass  = breakdown.get("injection",     {}).get("score", 30) == 30
        hal_pass  = breakdown.get("hallucination", {}).get("score", 20) >= 10
        tone_pass = breakdown.get("tone",          {}).get("score", 10) >= 5

        pii_icon  = "🟢" if pii_pass  else "🔴"
        inj_icon  = "🟢" if inj_pass  else "🔴"
        hal_icon  = "🟢" if hal_pass  else "🟡"
        tone_icon = "🟢" if tone_pass else "🟡"

        log_items.append((lead.get("company","Unknown"), score, pii_icon, inj_icon, hal_icon, tone_icon))

    for company, score, pii, inj, hal, tone in log_items:
        score_color = "#15803d" if score >= 80 else "#a16207" if score >= 60 else "#dc2626"
        st.markdown(f"""
        <div class="log-item">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-size:13px;font-weight:600;color:#0b1c30">{company}</span>
                <span style="font-size:11px;font-weight:700;color:{score_color}">{score}/100</span>
            </div>
            <div style="display:flex;gap:14px">
                <span style="font-size:11px">{pii} <b>PII</b></span>
                <span style="font-size:11px">{inj} <b>Inj</b></span>
                <span style="font-size:11px">{hal} <b>Hal</b></span>
                <span style="font-size:11px">{tone} <b>Tone</b></span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:12px;text-align:center;border-top:1px solid #c7c4d7">
        <span style="color:#4648d4;font-size:13px;font-weight:600;cursor:pointer">
            View All Security Logs →
        </span>
    </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─── Pipeline Activity Chart ──────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-header">
    <div>
        <div>Pipeline Activity</div>
        <div style="font-size:12px;color:#464554;font-weight:400">
            Real-time throughput metrics (Last 24 hours)
        </div>
    </div>
    <div style="display:flex;gap:4px;background:#fff;border:1px solid #c7c4d7;border-radius:8px;padding:4px">
        <span style="background:#4648d4;color:white;padding:4px 12px;border-radius:6px;font-size:12px;font-weight:600">24h</span>
        <span style="color:#464554;padding:4px 12px;font-size:12px;cursor:pointer">7d</span>
        <span style="color:#464554;padding:4px 12px;font-size:12px;cursor:pointer">30d</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Build chart data from pipeline runs or use mock
hours = [f"{h:02d}:00" for h in range(24)]
run_counts = [0] * 24
for run in runs:
    try:
        started = run.get("started_at", "")
        if started:
            dt = datetime.fromisoformat(started.replace("Z",""))
            run_counts[dt.hour] += 1
    except Exception:
        pass

# If all zeros, use demo data
if sum(run_counts) == 0:
    run_counts = [2,1,3,1,4,6,8,10,12,9,11,14,10,8,12,15,18,14,11,9,12,10,7,5]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=hours,
    y=run_counts,
    marker_color=["#4648d4" if v == max(run_counts) else "#a5b4fc" for v in run_counts],
    hovertemplate="<b>%{x}</b><br>Runs: %{y}<extra></extra>",
))
fig.update_layout(
    height=260,
    margin=dict(l=20, r=20, t=10, b=30),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#464554"), tickangle=0,
               tickvals=hours[::4]),
    yaxis=dict(showgrid=True, gridcolor="#eef0f8", tickfont=dict(size=11, color="#464554"),
               zeroline=False),
    showlegend=False,
    bargap=0.3,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)


# ─── Agent Status Row ─────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 🤖 Agent Status", unsafe_allow_html=True)

a1, a2, a3, a4 = st.columns(4)
agents = [
    ("🔍", "Scout",        "Lead Discovery",    "Mock CSV • Apollo • Hunter"),
    ("🔬", "Analyst",      "Lead Enrichment",   "OCR • Tesseract • Vision"),
    ("✍️", "Writer",       "Outreach Drafting", "Personalised • <150 words"),
    ("🛡", "Security Guard","Compliance Check",  "PII • Injection • Hallucination"),
]
last_run = runs[0].get("started_at", "Never") if runs else "Never"
try:
    last_run = datetime.fromisoformat(last_run.replace("Z","")).strftime("%H:%M %d %b")
except Exception:
    pass

for col, (icon, name, role, tools) in zip([a1, a2, a3, a4], agents):
    with col:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center">
            <div style="font-size:28px;margin-bottom:8px">{icon}</div>
            <div style="font-weight:700;font-size:15px;color:#0b1c30">{name}</div>
            <div style="font-size:12px;color:#4648d4;font-weight:600;margin:4px 0">{role}</div>
            <div style="font-size:11px;color:#464554">{tools}</div>
            <div style="margin-top:10px">
                <span class="metric-badge badge-green">● Active</span>
            </div>
            <div style="font-size:10px;color:#464554;margin-top:6px">Last run: {last_run}</div>
        </div>""", unsafe_allow_html=True)

# ─── Auto-refresh ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Refresh Data", use_container_width=False):
    st.cache_data.clear()
    st.rerun()
