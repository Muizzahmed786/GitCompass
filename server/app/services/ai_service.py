"""
AI Service — Integrates Gemini and Groq APIs to generate evolution summaries, architecture shifts, and answer Q&A.
Implements a multi-provider fallback architecture.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any

from app.services.ai_providers import generate_ai_response, AllProvidersFailedError
from app.services.ai_prompts import REPOSITORY_INTELLIGENCE_PROMPT, extract_json

logger = logging.getLogger("gitcompass.ai_service")


# ── AI Feature Functions ───────────────────────────────────────────────────


async def generate_evolution_summary(repo_name: str, evidence: dict, selected_model: str = "auto") -> dict:
    """Generates a structured developer-focused summary of the repository from evidence."""
    compact_evidence = json.dumps({
        "repository": evidence.get("repository"),
        "technology": evidence.get("technology"),
        "phases": evidence.get("phases"),
        "hotspots": evidence.get("hotspots"),
        "contributors": evidence.get("contributors"),
        "commit_sample": evidence.get("commit_sample")
    }, separators=(',', ':'))

    system_prompt = REPOSITORY_INTELLIGENCE_PROMPT
    user_prompt = f"""You are generating an AI Summary for the repository '{repo_name}'.
What is this repository, how is it built, how has it evolved, and what should a developer understand when onboarding?

Evidence (JSON):
{compact_evidence}

Return a JSON object with exactly this schema:
{{
  "what_is_this": "Evidence-supported description of what the repository appears to be. Use [UNKNOWN] if evidence is insufficient.",
  "technology_stack": {{
    "languages": [],
    "frameworks": [],
    "databases": [],
    "infrastructure": []
  }},
  "architecture_overview": "Evidence-supported description of the repository structure using directories and hotspots.",
  "evolution_summary": "Concise explanation of how the repository evolved across its chronological phases. Avoid generic statements.",
  "key_areas": [
    {{
      "area": "file or directory path",
      "why_important": "Evidence-supported explanation (e.g. churn, activity)."
    }}
  ],
  "onboarding_notes": "Important things a new developer should understand first. Use [UNKNOWN] if evidence is insufficient."
}}

Return ONLY valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
"""
    try:
        result = await generate_ai_response(
            task_type="evolution_summary",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            selected_model=selected_model
        )
        text = extract_json(result["text"], is_array=False)
        return json.loads(text)
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for summary: {exc}")
        raise ValueError(f"AI Analysis Unavailable: {exc}")
    except json.JSONDecodeError as exc:
        logger.error(f"Malformed JSON returned by provider: {exc}")
        raise ValueError(f"Failed to parse evolution summary from AI response: {exc}")
    except Exception as exc:
        logger.error(f"Failed to generate AI summary: {exc}")
        raise ValueError(f"Failed to generate AI summary: {exc}")


async def detect_architecture_shifts(repo_name: str, evidence: dict, selected_model: str = "auto") -> List[Dict]:
    """Detects major architectural shifts from deterministic phases (Stage 6)."""
    
    # We no longer limit based on total commits here because the evidence assembler already caps 
    # the evidence size (e.g. top 30 commits). The full context is bounded.
    phases = evidence.get("phases", [])

    compact_evidence = json.dumps({
        "repository": evidence.get("repository"),
        "technology": evidence.get("technology"),
        "phases": phases,
        "commit_sample": evidence.get("commit_sample")
    }, separators=(',', ':'))

    system_prompt = REPOSITORY_INTELLIGENCE_PROMPT
    user_prompt = f"""You are analyzing the architectural evolution of the repository '{repo_name}'.
You are receiving deterministic evidence including architectural phases, technology footprint, and significant commits.
If architectural phases are present, their boundaries are authoritative.
If phases are absent, synthesize a timeline of technology introductions and major shifts based on the commit_sample and technology footprint.
Do not invent dates or events that are not present in the evidence.

Evidence (JSON):
{compact_evidence}

Synthesize this evidence into a chronological timeline of architectural shifts.
Return a JSON array of objects. Each object must have exactly these keys:
{{
  "date": "YYYY-MM-DD (use phase start_date or commit date)",
  "title": "Short architectural label",
  "what_changed": "Concrete facts supported by evidence.",
  "architectural_significance": "Why this matters. Use [INFERENCE] when interpretation is involved.",
  "evidence_items": [
    "String items directly from the evidence (e.g. 'dependency_added: fastapi' or 'commit: <message>')"
  ]
}}

Return ONLY valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
"""
    try:
        result = await generate_ai_response(
            task_type="architecture_shifts",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            selected_model=selected_model
        )
        text = extract_json(result["text"], is_array=True)
        return json.loads(text)
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for shift detection: {exc}")
        raise ValueError(f"AI Analysis Unavailable: {exc}")
    except json.JSONDecodeError as exc:
        logger.error(f"Malformed JSON returned by provider: {exc}")
        raise ValueError(f"Failed to parse architecture shifts from AI response: {exc}")
    except Exception as exc:
        logger.error(f"Failed to detect architectural shifts: {exc}")
        raise ValueError(f"Failed to detect architectural shifts: {exc}")


async def answer_qa(
    repo_name: str, 
    history: List[Dict[str, str]], 
    evidence: dict, 
    page_context: Optional[dict] = None, 
    specific_slice: Optional[dict] = None,
    selected_model: str = "auto"
) -> dict:
    """Answers a Q&A question using the repository evidence and conversation history, returning JSON with citations."""
    compact_evidence = json.dumps({
        "evidence_status": evidence.get("evidence_status", "unknown"),
        "repository": evidence.get("repository"),
        "phases": evidence.get("phases"),
        "hotspots": evidence.get("hotspots"),
        "technology": evidence.get("technology"),
        "contributors": evidence.get("contributors"),
    }, separators=(',', ':'))

    system_prompt = REPOSITORY_INTELLIGENCE_PROMPT
    
    # Format the conversation history string
    history_str = ""
    for msg in history[:-1]:
        role_label = "Developer" if msg["role"] == "user" else "Analyst"
        history_str += f"{role_label}: {msg['content']}\n\n"
    
    current_question = history[-1]["content"] if history else ""

    user_prompt = f"""You are answering a question about the repository '{repo_name}'.

REPOSITORY EVIDENCE (JSON):
{compact_evidence}

PAGE CONTEXT (JSON):
{json.dumps(page_context) if page_context else "None"}

SPECIFIC EVIDENCE SLICE (JSON):
{json.dumps(specific_slice) if specific_slice else "None"}

CONVERSATION HISTORY:
{history_str if history_str else "No previous history."}

CURRENT QUESTION:
{current_question}

OUTPUT FORMAT RULES:
You MUST return ONLY a strictly valid JSON object matching this schema exactly. Do NOT wrap it in ```json blocks or include any extra text.

{{
  "answer": "Your markdown formatted answer here. Use clear formatting, bullet points, or code blocks where appropriate.",
  "citations": [
    {{
      "type": "file",
      "path": "path/to/file.ext"
    }}
  ]
}}

EVIDENCE RULES:
1. Grounding: Answer directly based ONLY on the available repository evidence.
2. Citations: Only include citations for files that are EXPLICITLY present in the 'SPECIFIC EVIDENCE SLICE' or the 'hotspots' section of the 'REPOSITORY EVIDENCE'. Do not invent citation paths.
3. Unknown: If the evidence doesn't support a definitive answer, clearly state that the evidence does not establish it. DO NOT fabricate historical reasons, file names, or architectural choices.
4. Contradictions: Correct user assumptions that contradict repository evidence.
5. Inference: Distinguish clearly between concrete facts and your own inferences.
"""
    try:
        
        result = await generate_ai_response(
            task_type="qa",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            selected_model=selected_model
        )
        text = result["text"].strip()
        
        # Clean markdown wrappers if present
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text).strip()
        
        parsed = json.loads(text)
        return {
            "answer": parsed.get("answer", "No answer provided in response."),
            "citations": parsed.get("citations", [])
        }
        
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse Q&A JSON response: {exc}")
        return {"answer": "AI Analysis Failed: The model returned a malformed response.", "citations": []}
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for Q&A: {exc}")
        return {"answer": f"AI Analysis Unavailable: {exc}", "citations": []}
    except Exception as exc:
        logger.error(f"Failed to answer question: {exc}")
        return {"answer": f"Failed to answer question: {exc}", "citations": []}


async def generate_development_story(repo_name: str, evidence: dict, selected_model: str = "auto") -> dict:
    """Generates a structured chronological story retelling how the repository evolved over time."""
    compact_evidence = json.dumps({
        "repository": evidence.get("repository"),
        "phases": evidence.get("phases"),
        "hotspots": evidence.get("hotspots"),
        "technology": evidence.get("technology"),
        "contributors": evidence.get("contributors"),
        "commit_sample": evidence.get("commit_sample")
    }, separators=(',', ':'))

    system_prompt = REPOSITORY_INTELLIGENCE_PROMPT
    user_prompt = f"""You are telling the development story of the repository '{repo_name}' based on its chronological evidence.
How did this repository evolve as software over time? Do not merely summarize commit counts.

Evidence (JSON):
{compact_evidence}

Return a JSON object with exactly this schema:
{{
  "phases": [
    {{
      "title": "Use the Stage 6 phase title",
      "period": "YYYY-MM-DD to YYYY-MM-DD (from Stage 6)",
      "narrative": "2-3 sentences explaining what happened and which areas were affected.",
      "key_files": ["files present in evidence"],
      "key_technologies": ["technologies supported by evidence"],
      "key_contributors": ["contributors supported by evidence"],
      "description": "Narrative paragraph explaining what actually happened in this phase and its engineering significance."
    }}
  ],
  "overall_arc": "One concise paragraph explaining the repository's overall evolution."
}}

Return ONLY valid JSON.
Do not wrap the response in markdown fences.
Do not add commentary before or after the JSON.
"""
    try:
        result = await generate_ai_response(
            task_type="development_story",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            selected_model=selected_model
        )
        text = extract_json(result["text"], is_array=False)
        return json.loads(text)
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for development story: {exc}")
        raise ValueError(f"AI Analysis Unavailable: {exc}")
    except json.JSONDecodeError as exc:
        logger.error(f"Malformed JSON returned by provider: {exc}")
        raise ValueError(f"Failed to parse development story from AI response: {exc}")
    except Exception as exc:
        logger.error(f"Failed to generate development story: {exc}")
        raise ValueError(f"Failed to generate development story: {exc}")




