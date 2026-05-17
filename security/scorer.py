"""
Security Scorer
---------------
Computes the composite Security Score (0–100) for each outreach message
by combining results from all three checks:

  Check              Max Points   Fail Behaviour
  ─────────────────────────────────────────────
  PII Detection         40        Hard fail (0 pts)
  Injection Detection   30        Hard fail (0 pts)
  Hallucination Check   20        Partial (0/10/20)
  Tone Check            10        Partial (0/5/10)
  ─────────────────────────────────────────────
  TOTAL                100

Approval threshold: score >= 70 → APPROVED
                    score <  70 → REJECTED
"""

import re
from dataclasses import dataclass, field
from loguru import logger

from security.checks.pii_check         import PIICheck
from security.checks.injection_check   import InjectionCheck
from security.checks.hallucination_check import HallucinationCheck


APPROVAL_THRESHOLD = 70


@dataclass
class SecurityReport:
    score:            int
    approved:         bool
    pii_score:        int
    injection_score:  int
    hallucination_score: int
    tone_score:       int
    pii_detail:       str = ""
    injection_detail: str = ""
    hallucination_detail: str = ""
    tone_detail:      str = ""
    rejection_reason: str = ""
    findings:         list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score":               self.score,
            "approved":            self.approved,
            "rejection_reason":    self.rejection_reason,
            "breakdown": {
                "pii":          {"score": self.pii_score,          "detail": self.pii_detail},
                "injection":    {"score": self.injection_score,    "detail": self.injection_detail},
                "hallucination":{"score": self.hallucination_score,"detail": self.hallucination_detail},
                "tone":         {"score": self.tone_score,         "detail": self.tone_detail},
            },
            "findings": self.findings,
        }


class SecurityScorer:
    """Runs all security checks and returns a composite SecurityReport."""

    def __init__(self):
        self.pii_check           = PIICheck()
        self.injection_check     = InjectionCheck()
        self.hallucination_check = HallucinationCheck()

    def score(self, message: str, lead_data: dict) -> SecurityReport:
        logger.info(f"Running security checks for lead: {lead_data.get('full_name', 'unknown')}")

        # ── Run all checks ────────────────────────────────────────────────────
        pii_result    = self.pii_check.run(message)
        inject_result = self.injection_check.run(message)
        halluc_result = self.hallucination_check.run(message, lead_data)
        tone_score, tone_detail = self._tone_check(message)

        # ── Compute total ─────────────────────────────────────────────────────
        total = (
            pii_result.score +
            inject_result.score +
            halluc_result.score +
            tone_score
        )
        approved = total >= APPROVAL_THRESHOLD

        # ── Build rejection reason ────────────────────────────────────────────
        reasons = []
        if not pii_result.passed:
            reasons.append(f"PII: {pii_result.detail}")
        if not inject_result.passed:
            reasons.append(f"Injection: {inject_result.detail}")
        if not halluc_result.passed:
            reasons.append(f"Hallucination: {halluc_result.detail}")
        if tone_score < 5:
            reasons.append(f"Tone: {tone_detail}")

        rejection_reason = " | ".join(reasons) if reasons else ""

        status = "APPROVED" if approved else "REJECTED"
        logger.info(f"Security Score: {total}/100 → {status}")

        return SecurityReport(
            score=total,
            approved=approved,
            pii_score=pii_result.score,
            injection_score=inject_result.score,
            hallucination_score=halluc_result.score,
            tone_score=tone_score,
            pii_detail=pii_result.detail,
            injection_detail=inject_result.detail,
            hallucination_detail=halluc_result.detail,
            tone_detail=tone_detail,
            rejection_reason=rejection_reason,
            findings=pii_result.findings,
        )

    # ── Tone Check (regex-based) ──────────────────────────────────────────────
    def _tone_check(self, message: str) -> tuple[int, str]:
        """
        Checks for overly salesy, spammy, or aggressive language.
        Returns (score, detail).
        """
        salesy_patterns = [
            re.compile(r"\b(act now|limited time|exclusive offer|don't miss out)\b", re.I),
            re.compile(r"\b(guaranteed|100%\s+free|no risk|money.back)\b", re.I),
            re.compile(r"!!+"),   # multiple exclamation marks
            re.compile(r"\b(buy now|click here|sign up today|get started now)\b", re.I),
            re.compile(r"\b(synergy|leverage|disruptive|game.changer|revolutionary)\b", re.I),
        ]

        hits = []
        for pattern in salesy_patterns:
            if pattern.search(message):
                hits.append(pattern.pattern)

        if len(hits) >= 3:
            return 0, f"Tone too salesy — {len(hits)} spam indicators found."
        elif len(hits) >= 1:
            return 5, f"Slightly salesy — {len(hits)} indicator(s) found: {hits[0]}"
        else:
            return 10, "Tone is professional and conversational."
