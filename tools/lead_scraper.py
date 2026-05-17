"""
Lead Scraper Tool
-----------------
Provides the Scout agent with leads from one of three sources:
  1. Mock CSV  — for local development (LEAD_SOURCE=mock)
  2. Apollo.io — free tier, 50 credits/month (LEAD_SOURCE=apollo)
  3. Hunter.io — free tier, 25 searches/month (LEAD_SOURCE=hunter)

Switch sources via the LEAD_SOURCE environment variable in .env

CrewAI 1.x note: _run() accepts a single string argument.
"""

import os
import json
import httpx
import pandas as pd
from pathlib import Path
from crewai.tools import BaseTool
from loguru import logger


DATA_DIR = Path(__file__).parent.parent / "data"


class LeadScraperTool(BaseTool):
    name: str = "Lead Scraper"
    description: str = (
        "Fetches a list of business prospects. "
        "Input format: 'industry=SaaS,job_title=Head of Growth,location=United States,limit=5' "
        "Returns a JSON list of leads with name, title, company, email, and source URL."
    )

    def _run(self, query: str = "") -> str:
        # Parse simple key=value input from the LLM
        params = _parse_query(query)

        source    = os.getenv("LEAD_SOURCE", "mock").lower()
        industry  = params.get("industry",  os.getenv("TARGET_INDUSTRY",  "SaaS"))
        job_title = params.get("job_title", os.getenv("TARGET_JOB_TITLE", "Head of Growth"))
        location  = params.get("location",  os.getenv("TARGET_LOCATION",  "United States"))
        limit     = int(params.get("limit", 5))

        logger.info(f"Scout → fetching leads | source={source} | industry={industry} | title={job_title}")

        if source == "apollo":
            return self._fetch_apollo(industry, job_title, location, limit)
        elif source == "hunter":
            return self._fetch_hunter(industry, job_title, location, limit)
        else:
            return self._fetch_mock(industry, job_title, location, limit)

    # ── Mock CSV ──────────────────────────────────────────────────────────────
    def _fetch_mock(self, industry, job_title, location, limit) -> str:
        csv_path = DATA_DIR / "mock_leads.csv"
        df = pd.read_csv(csv_path)

        filtered = df[
            df["industry"].str.contains(industry, case=False, na=False) |
            df["job_title"].str.contains(job_title, case=False, na=False)
        ].head(limit)

        if filtered.empty:
            filtered = df.head(limit)

        leads = filtered.to_dict(orient="records")
        for lead in leads:
            lead["source"] = "mock"

        logger.success(f"Mock dataset returned {len(leads)} leads")
        return json.dumps(leads, indent=2)

    # ── Apollo.io ─────────────────────────────────────────────────────────────
    def _fetch_apollo(self, industry, job_title, location, limit) -> str:
        api_key = os.getenv("APOLLO_API_KEY")
        if not api_key:
            raise ValueError("APOLLO_API_KEY not set in .env")

        url = "https://api.apollo.io/v1/mixed_people/search"
        payload = {
            "api_key": api_key,
            "q_keywords": job_title,
            "person_titles": [job_title],
            "person_locations": [location],
            "per_page": limit,
        }

        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        leads = []
        for person in data.get("people", []):
            leads.append({
                "full_name":    person.get("name"),
                "job_title":    person.get("title"),
                "company":      person.get("organization", {}).get("name"),
                "industry":     industry,
                "location":     location,
                "email":        person.get("email"),
                "linkedin_url": person.get("linkedin_url"),
                "source_url":   person.get("organization", {}).get("website_url"),
                "source":       "apollo",
            })

        logger.success(f"Apollo returned {len(leads)} leads")
        return json.dumps(leads, indent=2)

    # ── Hunter.io ─────────────────────────────────────────────────────────────
    def _fetch_hunter(self, industry, job_title, location, limit) -> str:
        api_key = os.getenv("HUNTER_API_KEY")
        if not api_key:
            raise ValueError("HUNTER_API_KEY not set in .env")

        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "api_key": api_key,
            "type":    "personal",
            "limit":   limit,
        }

        response = httpx.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        leads = []
        for email_data in data.get("data", {}).get("emails", []):
            leads.append({
                "full_name":    f"{email_data.get('first_name', '')} {email_data.get('last_name', '')}".strip(),
                "job_title":    email_data.get("position"),
                "company":      data["data"].get("organization"),
                "industry":     industry,
                "location":     location,
                "email":        email_data.get("value"),
                "linkedin_url": email_data.get("linkedin"),
                "source_url":   data["data"].get("domain"),
                "source":       "hunter",
            })

        logger.success(f"Hunter.io returned {len(leads)} leads")
        return json.dumps(leads, indent=2)


def _parse_query(query: str) -> dict:
    """Parse 'key=value,key=value' string into a dict."""
    result = {}
    if not query:
        return result
    for part in query.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
    return result
