"""
The Analyst Agent
-----------------
Role:     Lead Intelligence Analyst
Goal:     Enrich each lead with deep context extracted from company visuals,
          banners, and public pages using OCR and reasoning.
Backstory: A sharp-eyed analyst who can pull signal from any source —
           including images, banners, and graphics others overlook.

Tools:    OCRTool (Tesseract-powered image text extraction)
"""

import os
from crewai import Agent
from tools.ocr_tool import OCRTool
from loguru import logger


def build_analyst() -> Agent:
    llm  = _get_llm()
    tool = OCRTool()

    logger.info("Building Analyst agent")

    return Agent(
        role="Lead Intelligence Analyst",
        goal=(
            "For each lead provided, extract key facts that would help craft a "
            "highly personalised outreach message. Use OCR on any available image URLs. "
            "Identify: recent company milestones, product focus areas, team culture signals, "
            "and any pain points visible in their public presence."
        ),
        backstory=(
            "You are a meticulous intelligence analyst with a rare skill: you can extract "
            "meaningful business signals from even the most mundane sources — a company banner, "
            "a conference slide, a product screenshot. You've built dossiers on thousands of "
            "companies and you know exactly what detail makes an outreach message feel "
            "researched rather than generic. You never guess; you only report what you can verify."
        ),
        tools=[tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )


def _get_llm() -> str:
    model = os.getenv("OLLAMA_MODEL", "llama3")
    return f"ollama/{model}"
