"""
PII Check
---------
Detects Personally Identifiable Information in the Writer's outreach message.
Uses regex patterns for fast, deterministic detection.

Checks for:
  - Email addresses
  - Phone numbers (US and international formats)
  - Social Security Numbers
  - Credit card numbers

Scoring:
  - No PII found     → +40 points (full score)
  - PII detected     →   0 points (hard fail)
"""

import re
from dataclasses import dataclass, field
from loguru import logger


# ─── PII Patterns ─────────────────────────────────────────────────────────────

PII_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
    ),
    "phone_us": re.compile(
        r"\b(\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"
    ),
    "phone_international": re.compile(
        r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{1,4}[\s\-.]?\d{1,9}"
    ),
    "ssn": re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    ),
    "credit_card": re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    ),
}

MAX_SCORE = 40


@dataclass
class PIIResult:
    passed: bool
    score: int
    findings: list = field(default_factory=list)
    detail: str = ""


class PIICheck:
    """Scans outreach message for PII and returns a score + findings."""

    def run(self, message: str) -> PIIResult:
        findings = []

        for pii_type, pattern in PII_PATTERNS.items():
            matches = pattern.findall(message)
            if matches:
                findings.append({
                    "type":    pii_type,
                    "matches": [str(m) for m in matches[:3]],  # cap at 3 examples
                })

        if findings:
            types_found = ", ".join(f["type"] for f in findings)
            logger.warning(f"PII detected: {types_found}")
            return PIIResult(
                passed=False,
                score=0,
                findings=findings,
                detail=f"PII detected — types found: {types_found}. Remove all personal identifiers.",
            )

        logger.success("PII check passed — no PII detected")
        return PIIResult(
            passed=True,
            score=MAX_SCORE,
            findings=[],
            detail="No PII detected.",
        )
