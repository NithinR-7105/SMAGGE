"""
Security Guard
--------------
The main entry point for Phase 2's security layer.

Intercepts every outreach message from the Writer and runs it through
the full security pipeline:
  1. PII Check        — strips/flags personal identifiers
  2. Injection Check  — blocks prompt hijacking attempts
  3. Hallucination    — cross-references facts against Scout data
  4. Tone Check       — ensures professional, non-spammy language

Each message gets a Security Score (0–100).
Messages scoring >= 70 are APPROVED and saved to the database.
Messages scoring <  70 are REJECTED with a detailed reason logged.

NeMo Guardrails Integration:
  The guardrails/ folder contains the Colang config that wraps this
  logic in NVIDIA's NeMo Guardrails framework for enterprise-grade
  auditability (used in Phase 3 for the dashboard security log).
"""

import json
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel
from loguru       import logger

from security.scorer import SecurityScorer, SecurityReport


console = Console()


class SecurityGuard:
    """
    Intercepts Writer output and applies all security checks.
    Returns enriched lead list with security scores attached.
    """

    def __init__(self):
        self.scorer = SecurityScorer()

    def process(self, leads_with_outreach: list) -> list:
        """
        Args:
            leads_with_outreach: List of lead dicts, each with 'message' and
                                 'subject_line' fields added by the Writer.

        Returns:
            Same list with 'security_score', 'security_log', and 'status'
            fields added to each lead.
        """
        console.print(Panel.fit(
            "[bold magenta]🛡  Security Guard — Intercepting Writer Output[/bold magenta]",
            border_style="magenta"
        ))

        results   = []
        approved  = 0
        rejected  = 0

        for lead in leads_with_outreach:
            message = lead.get("message", "")
            name    = lead.get("full_name", "Unknown")

            if not message:
                logger.warning(f"No message found for {name} — skipping security check.")
                lead["security_score"] = 0
                lead["security_log"]   = {}
                lead["status"]         = "rejected"
                lead["rejection_reason"] = "Writer produced no message."
                results.append(lead)
                continue

            # Run the full security check
            report: SecurityReport = self.scorer.score(message, lead)

            # Attach results to the lead
            lead["security_score"]    = report.score
            lead["security_log"]      = report.to_dict()
            lead["status"]            = "approved" if report.approved else "rejected"
            lead["rejection_reason"]  = report.rejection_reason

            if report.approved:
                approved += 1
            else:
                rejected += 1

            # Print per-lead result
            self._print_lead_result(name, lead.get("company", ""), report)
            results.append(lead)

        # Summary table
        self._print_summary(approved, rejected, len(leads_with_outreach))
        return results

    def _print_lead_result(self, name: str, company: str, report: SecurityReport):
        status_icon  = "✅" if report.approved else "❌"
        status_color = "green" if report.approved else "red"

        console.print(
            f"\n[bold]{status_icon} {name}[/bold] @ {company}  "
            f"[{status_color}]Score: {report.score}/100[/{status_color}]"
        )
        console.print(
            f"   PII: {report.pii_score}/40  "
            f"Injection: {report.injection_score}/30  "
            f"Hallucination: {report.hallucination_score}/20  "
            f"Tone: {report.tone_score}/10"
        )
        if not report.approved:
            console.print(f"   [red]Rejection reason: {report.rejection_reason}[/red]")

    def _print_summary(self, approved: int, rejected: int, total: int):
        table = Table(title="\n🛡  Security Guard Summary", border_style="magenta")
        table.add_column("Metric",   style="cyan")
        table.add_column("Count",    style="white")
        table.add_column("Rate",     style="white")

        table.add_row("Total processed", str(total),    "100%")
        table.add_row("Approved",        str(approved),  f"{approved/total*100:.0f}%")
        table.add_row("Rejected",        str(rejected),  f"{rejected/total*100:.0f}%")

        console.print(table)
