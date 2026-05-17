-- ─── SMAGGE Database Schema ──────────────────────────────────────────────────
-- Phase 1: Core tables for leads and pipeline runs
-- Phase 3 will add security_score and feedback columns

-- Leads table: every prospect discovered by the Scout
CREATE TABLE IF NOT EXISTS leads (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(255),
    job_title       VARCHAR(255),
    company         VARCHAR(255),
    industry        VARCHAR(255),
    location        VARCHAR(255),
    email           VARCHAR(255),
    linkedin_url    TEXT,
    source_url      TEXT,
    source          VARCHAR(50) DEFAULT 'mock',   -- 'apollo', 'hunter', 'mock'
    raw_data        JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Analyses table: OCR + enrichment output from the Analyst
CREATE TABLE IF NOT EXISTS analyses (
    id              SERIAL PRIMARY KEY,
    lead_id         INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    ocr_text        TEXT,
    extracted_facts JSONB,      -- structured facts pulled from company visuals
    analyst_notes   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Outreach table: messages drafted by the Writer
CREATE TABLE IF NOT EXISTS outreach (
    id              SERIAL PRIMARY KEY,
    lead_id         INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    analysis_id     INTEGER REFERENCES analyses(id),
    message         TEXT,
    subject_line    VARCHAR(500),
    status          VARCHAR(50) DEFAULT 'pending',  -- pending | approved | rejected
    rejection_reason TEXT,                           -- Phase 3: feedback loop
    security_score  INTEGER,                         -- Phase 2: 0–100
    security_log    JSONB,                           -- Phase 2: per-check breakdown
    created_at      TIMESTAMP DEFAULT NOW(),
    reviewed_at     TIMESTAMP
);

-- Pipeline runs table: tracks each full Scout→Analyst→Writer execution
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              SERIAL PRIMARY KEY,
    status          VARCHAR(50) DEFAULT 'running',  -- running | completed | failed
    leads_found     INTEGER DEFAULT 0,
    leads_processed INTEGER DEFAULT 0,
    trigger_source  VARCHAR(100) DEFAULT 'manual',  -- 'manual', 'n8n_webhook', 'n8n_timer'
    error_message   TEXT,
    started_at      TIMESTAMP DEFAULT NOW(),
    completed_at    TIMESTAMP
);

-- ─── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_leads_company   ON leads(company);
CREATE INDEX IF NOT EXISTS idx_leads_source    ON leads(source);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
CREATE INDEX IF NOT EXISTS idx_outreach_lead   ON outreach(lead_id);
