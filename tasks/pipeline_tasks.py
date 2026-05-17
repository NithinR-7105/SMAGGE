"""
Pipeline Tasks
--------------
Defines the three CrewAI tasks that form the Scout → Analyst → Writer chain.
Each task receives the output of the previous one as context.
"""

from crewai import Task
from crewai import Agent


def build_scout_task(scout: Agent, industry: str, job_title: str, location: str, limit: int = 5) -> Task:
    return Task(
        description=(
            f"Search for {limit} business prospects in the **{industry}** industry "
            f"with the job title **{job_title}** located in **{location}**. "
            "For each lead, collect: full name, job title, company name, industry, "
            "location, email (if available), LinkedIn URL, and source URL. "
            "Return results as a JSON array."
        ),
        expected_output=(
            "A JSON array of lead objects. Each object must have: "
            "full_name, job_title, company, industry, location, email, linkedin_url, source_url, source."
        ),
        agent=scout,
    )


def build_analyst_task(analyst: Agent, scout_task: Task) -> Task:
    return Task(
        description=(
            "For each lead in the Scout's output, perform deep enrichment:\n"
            "1. If a source_url is provided, use OCR on any available company image/banner.\n"
            "2. Identify 2-3 specific, verifiable facts about the company or role "
            "   (recent milestones, product focus, culture signals, pain points).\n"
            "3. Note any detail that would make a cold outreach feel researched and personal.\n"
            "Return an enriched version of each lead with an 'analyst_notes' field added."
        ),
        expected_output=(
            "The original lead array enriched with an 'analyst_notes' field for each lead. "
            "analyst_notes should be a 2-3 sentence summary of the most relevant, "
            "specific facts found. No guessing — only report verifiable information."
        ),
        agent=analyst,
        context=[scout_task],
    )


def build_writer_task(writer: Agent, analyst_task: Task) -> Task:
    return Task(
        description=(
            "For each enriched lead from the Analyst, write a personalised outreach message:\n"
            "1. Draft a subject line (under 10 words, curiosity-driven, no clickbait).\n"
            "2. Write the message body (under 150 words).\n"
            "3. Reference at least ONE specific fact from the analyst_notes.\n"
            "4. End with a single, low-friction call to action.\n"
            "5. Do NOT include any phone numbers, emails, or sensitive PII in the message body.\n"
            "Return results as a JSON array with 'subject_line' and 'message' fields added."
        ),
        expected_output=(
            "The enriched lead array with two new fields per lead: "
            "'subject_line' (string) and 'message' (string). "
            "Messages must be conversational, specific, and under 150 words."
        ),
        agent=writer,
        context=[analyst_task],
    )
