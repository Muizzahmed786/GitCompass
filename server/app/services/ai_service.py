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
    """Generates an executive narrative of codebase evolution using Gemini."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    # Format metrics into structured context for the prompt
    hotspot_summary = "\n".join(
        [f"- {h['file_path']} ({h['commits_count']} commits, top author: {h['top_author']})" for h in hotspots[:5]]
    )

    prompt = f"""
You are an expert lead software architect auditing the repository '{repo_name}'.
Based on the following extracted Git analytical metrics, write a concise 3-paragraph executive architectural report.

Metrics:
- Repository Bus Factor: {bus_factor}
- Top Volatile Files (Hotspots):
{hotspot_summary}

Report Structure:
1. Architectural Churn & Focus Areas
2. Knowledge Risk & Ownership Assessment
3. Recommended Refactoring Actions
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed for summary: %s", exc)
        return f"Failed to generate AI summary: {exc}"


async def detect_architecture_shifts(repo_name: str, total_commits: int, significant_commits: List[Dict]) -> List[Dict]:
    """
    Detects major architectural shifts from commit history.
    Limits processing to repositories with <= MAX_COMMITS_FOR_SHIFT_DETECTION to prevent excessive token usage.
    """
    if total_commits > settings.MAX_COMMITS_FOR_SHIFT_DETECTION:
        raise ValueError(f"Repository exceeds the {settings.MAX_COMMITS_FOR_SHIFT_DETECTION} commit limit for shift detection (has {total_commits}).")

    client = get_gemini_client()
    if not client:
        raise ValueError("AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured.")

    commits_text = "\n".join(
        [f"[{c['committed_at']}] {c['author_name']}: {c['message']}" for c in significant_commits]
    )

    prompt = f"""
You are an expert software architect analyzing the commit history of the repository '{repo_name}'.
Review the following chronological list of significant commits (features, refactors, fixes).

Commit History:
{commits_text}

Identify up to 5 major "Architecture Shifts" (e.g., framework migrations, major refactors, dependency overhauls).
Return ONLY a valid JSON array of objects. Do not include markdown formatting or backticks.
Each object must have:
- "date": The date of the shift (YYYY-MM-DD).
- "title": A short title for the shift (max 50 chars).
- "description": A concise 1-sentence explanation of what changed and why.
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
        if text.startswith("```json"):
            text = text[7:-3].strip()
        
        return json.loads(text)
    except Exception as exc:
        logger.error("Gemini API call failed for shift detection: %s", exc)
        raise ValueError(f"Failed to detect architecture shifts: {exc}")


async def answer_qa(repo_name: str, question: str, context_summary: str) -> str:
    """Answers user queries about the repository using context."""
    client = get_gemini_client()
    if not client:
        return "AI Analysis Unavailable: GEMINI_API_KEY environment variable is not configured."

    prompt = f"""
You are a helpful Onboarding Assistant for the repository '{repo_name}'.
Use the following architectural context to answer the user's question accurately. If the context doesn't contain the answer, say so, but try to provide general architectural guidance.

Repository Context:
{context_summary}

User Question: {question}

Answer concisely and clearly.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.5)
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed for Q&A: %s", exc)
        return f"Failed to answer question: {exc}"
