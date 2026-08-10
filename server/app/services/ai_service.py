"""
AI Service — Integrates Gemini API to generate evolution summaries, architecture shifts, and answer Q&A.
"""

import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger("gitcompass.ai_service")


def get_gemini_client() -> Optional[genai.Client]:
    """Factory to initialize Gemini Client if API key is configured."""
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not configured.")
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_evolution_summary(repo_name: str, hotspots: List[Dict], bus_factor: int) -> str:
    """Generates a concise developer-focused summary of the repository."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    hotspot_lines = "\n".join(
        [f"- {h['file_path']} ({h['commits_count']} commits, top author: {h['top_author']})"
         for h in hotspots[:10]]
    ) or "No hotspot data available."

    prompt = f"""You are analyzing a software repository called '{repo_name}' based on its Git history metrics.

Data:
- Bus Factor: {bus_factor} (number of contributors responsible for 50%+ of commits)
- Top files by commit frequency:
{hotspot_lines}

Write a short, factual summary (3 short paragraphs, plain developer language) covering:
1. What the commit data suggests about which parts of the codebase are most actively developed
2. What the bus factor and file ownership data indicates about team structure and risk
3. Any concrete observations about code health based on the data (no speculation)

Rules:
- Write like a senior engineer summarizing metrics to a teammate, not an executive report
- Do not use words like "robust", "pivotal", "paramount", "leverage", or "strategic"
- Do not recommend actions unless directly supported by the data
- Be direct and brief. Each paragraph should be 2-3 sentences max
- Use plain markdown (bold for file names is fine, no excessive headers)
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
