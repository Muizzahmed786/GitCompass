"""
AI Service — Integrates Gemini API to generate evolution summaries, architecture shifts, and answer Q&A.
"""

import logging
from typing import Dict, List, Optional
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types

from app.config import settings

logger = logging.getLogger("gitcompass.ai_service")


def get_gemini_client() -> Optional[genai.Client]:
    """Factory to initialize Gemini Client if API key is configured."""
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not configured.")
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_evolution_summary(repo_name: str, aggregated_data: dict) -> str:
    """Generates a concise developer-focused summary of the repository from aggregated JSON data."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    import json
    # Minified JSON to save tokens
    compact_json = json.dumps(aggregated_data, separators=(',', ':'))

    prompt = f"""You are analyzing a software repository called '{repo_name}' based on its Git history metrics.

Aggregated Data (JSON):
{compact_json}

Write a short, factual summary covering exactly the following three sections. You must use these exact markdown subheadings for each section:

### Most Modified Files
List the most actively developed files and their commit counts using concrete statistics.

### Contributors & Ownership
State the bus factor and describe the distribution of authorship among top authors using concrete statistics. Report Git authorship only; DO NOT infer actual knowledge, responsibility, expertise, or code ownership beyond the recorded commit data.

### Development Patterns
Note any observable patterns in the data (e.g., if development is concentrated in specific directories or file types).

CRITICAL RULES:
- Summarize the data; DO NOT assess it.
- Describe raw Git statistics first, then state only directly observable patterns from those statistics.
- DO NOT invent risks, conclusions, or recommendations. Do not use words like "risk", "danger", "should", "recommend", or "mitigate" unless explicitly supported by the data.
- Do not use filler words like "robust", "pivotal", "paramount", "leverage", or "strategic".
- Be direct and brief. Each section must be exactly 1 paragraph of 2-3 concise sentences max.
- Do not add any new sections, recommendations, conclusions, or commentary outside these three sections.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed for summary: %s", exc)
        return f"Failed to generate AI summary: {exc}"


async def detect_architecture_shifts(repo_name: str, total_commits: int, significant_commits: List[Dict]) -> List[Dict]:
    """
    Detects major architectural shifts from commit history.
    Limits processing to repositories with <= MAX_COMMITS_FOR_SHIFT_DETECTION.
    """
    if total_commits > settings.MAX_COMMITS_FOR_SHIFT_DETECTION:
        raise ValueError(
            f"This repository has {total_commits} commits, which exceeds the {settings.MAX_COMMITS_FOR_SHIFT_DETECTION}-commit limit for shift detection. "
            f"This limit exists to control token usage. You can raise it in config if needed."
        )

    client = get_gemini_client()
    if not client:
        raise ValueError("AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured.")

    if not significant_commits:
        raise ValueError("No commits found for this repository.")

    commits_text = "\n".join(
        [f"[{c.get('committed_at', '')[:10]}] {c.get('author_name', 'unknown')}: {c.get('message', '')}"
         for c in significant_commits]
    )

    prompt = f"""You are analyzing the commit history of the repository '{repo_name}'.

Commit history:
{commits_text}

Identify up to 5 significant changes in the project's direction or structure — things like: switching frameworks, major refactors, adding or removing major features, changing the build system, or shifting architectural patterns.

Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.
Each object must have exactly these keys:
- "date": "YYYY-MM-DD"
- "title": short label (max 8 words)
- "description": one factual sentence about what changed, based only on the commit messages

If you cannot identify clear architectural shifts from the commit history, return an empty array: []
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        import json
        text = response.text.strip()
        # Strip markdown code fences if model ignores instructions
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3].strip()

        return json.loads(text)
    except Exception as exc:
        logger.error("Gemini API call failed for shift detection: %s", exc)
        raise ValueError(f"Failed to detect architecture shifts: {exc}")


async def answer_qa(repo_name: str, question: str, context_summary: str) -> str:
    """Answers user queries about the repository using context."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    prompt = f"""You are a technical assistant for the repository '{repo_name}'.

Repository context (from Git history analysis):
{context_summary}

Developer's question: {question}

Answer directly based on the available data. If the data doesn't support a definitive answer, say so clearly and briefly. 
Keep your answer concise and technical. Use markdown for formatting where it helps readability (e.g. bold file names, code blocks for paths).
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed for Q&A: %s", exc)
        return f"Failed to answer question: {exc}"


async def generate_development_story(repo_name: str, timeline_data: dict) -> str:
    """Generates a non-technical, chronological story retelling how the repository evolved over time."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    import json
    compact_json = json.dumps(timeline_data, separators=(',', ':'))

    prompt = f"""You are telling the development story of the repository '{repo_name}' based on its chronological Git history summary.

Chronological Timeline Summary (JSON):
{compact_json}

Write a short, intuitive, chronological story explaining how this project came together over time.

STRICT RULES:
- Use simple, approachable language. Feel like a concise narrative rather than a list of Git statistics.
- Connect related changes into a coherent progression over time.
- Only use information supported by the provided timeline summary.
- NEVER invent developer intentions, motivations, unevidenced features, architectural decisions, or events that are not in the data.
- Avoid excessive technical terminology or dramatic/marketing-style language.
- Structure it with short chronological phase indicators (e.g., **Getting Started → Building Core Features → Recent Progression** or similar), including ONLY phases supported by the data.
- CRITICAL: If the timeline data is too sparse or history is insufficient to form a story, explicitly state: "The available repository history is insufficient to establish a clear story."
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed for development story: %s", exc)
        return f"Failed to generate development story: {exc}"



