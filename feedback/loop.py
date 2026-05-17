"""
Feedback Loop
-------------
Phase 3 addition: Queries the database for previously REJECTED outreach
messages and their rejection reasons, then passes them to the Writer agent
as learning context so future drafts improve over time.

How it works:
  1. Before each pipeline run, query outreach table for rejected messages
  2. Group rejection reasons by type (PII / Injection / Hallucination / Tone)
  3. Format as a concise learning summary
  4. Inject into the Writer's backstory via build_writer(feedback_context=...)

This closes the loop: the system learns from its own mistakes.
"""

import os
import psycopg2
from loguru import logger


class FeedbackLoop:
    """Pulls rejection history from DB and formats it for the Writer agent."""

    def __init__(self):
        self.db_config = {
            "host":     os.getenv("POSTGRES_HOST",     "localhost"),
            "port":     int(os.getenv("POSTGRES_PORT", 5432)),
            "dbname":   os.getenv("POSTGRES_DB",       "smagge_db"),
            "user":     os.getenv("POSTGRES_USER",     "smagge"),
            "password": os.getenv("POSTGRES_PASSWORD", "smagge_secret"),
        }

    def get_feedback_context(self, limit: int = 10) -> str:
        """
        Returns a formatted string summarising recent rejection reasons.
        Returns empty string if no rejections or DB unavailable.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur  = conn.cursor()

            cur.execute("""
                SELECT
                    o.rejection_reason,
                    o.security_score,
                    o.message,
                    l.company,
                    l.job_title
                FROM outreach o
                JOIN leads l ON o.lead_id = l.id
                WHERE o.status = 'rejected'
                  AND o.rejection_reason IS NOT NULL
                  AND o.rejection_reason != ''
                ORDER BY o.created_at DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()
            cur.close()
            conn.close()

            if not rows:
                logger.info("No rejected messages found in DB — starting fresh.")
                return ""

            logger.info(f"Loaded {len(rows)} rejection(s) for Writer feedback context.")
            return self._format_feedback(rows)

        except Exception as e:
            logger.warning(f"Could not load feedback from DB ({e}). Writer will start fresh.")
            return ""

    def _format_feedback(self, rows: list) -> str:
        """Format DB rows into a concise learning summary for the Writer."""
        lines = [f"You have {len(rows)} past rejection(s) to learn from:\n"]

        for i, (reason, score, message, company, title) in enumerate(rows, 1):
            snippet = message[:100] + "..." if message and len(message) > 100 else message
            lines.append(
                f"{i}. Target: {title} @ {company}\n"
                f"   Score: {score}/100\n"
                f"   Reason: {reason}\n"
                f"   Message snippet: \"{snippet}\"\n"
            )

        lines.append(
            "\nApply these lessons:\n"
            "- Never include emails, phone numbers, or other PII in the message body.\n"
            "- Only reference facts that appear in the analyst notes.\n"
            "- Keep the tone conversational — avoid sales buzzwords.\n"
            "- Write under 150 words with a single clear call to action.\n"
        )

        return "\n".join(lines)

    def log_approval_decision(self, outreach_id: int, approved: bool, reason: str = ""):
        """
        Optionally called from the dashboard Approve/Reject buttons (Phase 4)
        to update outreach status based on human review.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur  = conn.cursor()

            status = "approved" if approved else "rejected"
            cur.execute("""
                UPDATE outreach
                SET status=%s, rejection_reason=%s, reviewed_at=NOW()
                WHERE id=%s
            """, (status, reason, outreach_id))

            conn.commit()
            cur.close()
            conn.close()
            logger.success(f"Outreach #{outreach_id} marked as {status}.")

        except Exception as e:
            logger.error(f"Could not update approval decision: {e}")
