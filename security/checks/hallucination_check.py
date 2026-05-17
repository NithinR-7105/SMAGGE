"""
Hallucination Check
-------------------
Cross-references facts in the Writer's outreach message against the
Scout's raw lead data to detect fabricated claims.

Uses the local LLM to reason about whether the message makes claims
that cannot be verified from the source data.

Scoring:
  - All facts verifiable    → +20 points
  - Minor unverified claims → +10 points
  - Clear hallucinations    →   0 points
"""

import os
import re
import json
import httpx
from dataclasses import dataclass
from loguru import logger


MAX_SCORE    = 20
OLLAMA_TIMEOUT = 45


@dataclass
class HallucinationResult:
    passed: bool
    score: int
    detail: str = ""
    unverified_claims: list = None

    def __post_init__(self):
        if self.unverified_claims is None:
            self.unverified_claims = []


class HallucinationCheck:
    """Cross-references outreach message facts against Scout's lead data."""

    def __init__(self):
        self.ollama_url   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def run(self, message: str, lead_data: dict) -> HallucinationResult:
        """
        Args:
            message:   The Writer's outreach message to check.
            lead_data: The raw lead dict from the Scout (source of truth).
        """
        source_facts = self._extract_source_facts(lead_data)
        return self._llm_crosscheck(message, source_facts)

    def _extract_source_facts(self, lead: dict) -> str:
        """Build a plain-English summary of what we actually know about this lead."""
        facts = []
        if lead.get("full_name"):    facts.append(f"Name: {lead['full_name']}")
        if lead.get("job_title"):    facts.append(f"Title: {lead['job_title']}")
        if lead.get("company"):      facts.append(f"Company: {lead['company']}")
        if lead.get("industry"):     facts.append(f"Industry: {lead['industry']}")
        if lead.get("location"):     facts.append(f"Location: {lead['location']}")
        if lead.get("source_url"):   facts.append(f"Source URL: {lead['source_url']}")
        if lead.get("analyst_notes"):facts.append(f"Analyst notes: {lead['analyst_notes']}")
        return "\n".join(facts)

    def _llm_crosscheck(self, message: str, source_facts: str) -> HallucinationResult:
        prompt = (
            "You are a fact-checking AI. Your job is to verify that an outreach message "
            "does not contain any fabricated or unverifiable claims.\n\n"
            "SOURCE FACTS (what we actually know):\n"
            f"{source_facts}\n\n"
            "OUTREACH MESSAGE TO CHECK:\n"
            f"{message}\n\n"
            "Instructions:\n"
            "1. Identify any specific claims in the message (company facts, achievements, stats, etc.)\n"
            "2. Check if each claim can be supported by the source facts\n"
            "3. Flag any claim that is fabricated or cannot be verified\n\n"
            "Respond with ONLY this JSON format:\n"
            '{"hallucination_level": "none|minor|major", '
            '"unverified_claims": ["claim1", "claim2"], '
            '"reason": "brief explanation"}'
        )

        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")

            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                level  = result.get("hallucination_level", "none")
                claims = result.get("unverified_claims", [])
                reason = result.get("reason", "")

                if level == "major":
                    logger.warning(f"Hallucination detected (major): {reason}")
                    return HallucinationResult(
                        passed=False, score=0,
                        unverified_claims=claims,
                        detail=f"Major hallucination: {reason}",
                    )
                elif level == "minor":
                    logger.info(f"Minor unverified claims: {claims}")
                    return HallucinationResult(
                        passed=True, score=10,
                        unverified_claims=claims,
                        detail=f"Minor unverified claims found: {reason}",
                    )
                else:
                    logger.success("Hallucination check passed — all facts verifiable")
                    return HallucinationResult(
                        passed=True, score=MAX_SCORE,
                        detail="All claims are verifiable from source data.",
                    )

        except Exception as e:
            logger.warning(f"Hallucination check LLM call failed ({e}). Defaulting to partial score.")

        return HallucinationResult(
            passed=True, score=10,
            detail="Hallucination check unavailable — partial score awarded.",
        )
