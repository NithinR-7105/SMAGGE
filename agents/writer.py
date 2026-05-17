"""
The Writer Agent
----------------
Role:     Hyper-Personalised Outreach Specialist
Goal:     Draft compelling, human-sounding outreach messages that reference
          specific, verified facts from the Analyst's findings.
Backstory: A copywriter who has never sent a generic cold email in their life —
           every message reads like it was written by someone who did their homework.

Tools:    None (the Writer reasons from the Analyst's context output)

Phase 3 addition: The Writer will also receive feedback from the approval loop
                  (rejected messages + reasons) to improve future drafts.
"""

import os
from crewai import Agent
from loguru import logger


def build_writer(feedback_context: str = "") -> Agent:
    llm = _get_llm()

    # Phase 3: inject feedback from the approval loop into the backstory
    feedback_section = ""
    if feedback_context:
        feedback_section = (
            f"\n\nLearning from past rejections:\n{feedback_context}\n"
            "Apply these lessons to avoid the same mistakes."
        )

    logger.info("Building Writer agent")

    return Agent(
        role="Hyper-Personalised Outreach Specialist",
        goal=(
            "Using the enriched lead profile and intelligence provided by the Analyst, "
            "write a short, compelling outreach message (under 150 words) and a subject line. "
            "The message must reference at least one specific, verified fact about the lead's "
            "company or role. It must NOT contain any PII beyond the lead's first name and company. "
            "Tone: conversational, peer-to-peer, never salesy."
        ),
        backstory=(
            "You are a world-class B2B copywriter who has never sent a generic cold message. "
            "Every piece of outreach you write feels like it came from someone who genuinely "
            "did their homework. You know that the difference between a reply and a delete is "
            "one specific, surprising detail that shows you actually understand their world. "
            "You write short. You write human. You write with a clear, single call to action."
            + feedback_section
        ),
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def _get_llm() -> str:
    model = os.getenv("OLLAMA_MODEL", "llama3")
    return f"ollama/{model}"
