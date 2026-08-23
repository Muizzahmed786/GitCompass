"""
AI Service — Integrates Gemini and Groq APIs to generate evolution summaries, architecture shifts, and answer Q&A.
Implements a multi-provider fallback architecture.
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

import httpx
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from google.genai.errors import APIError

from app.config import settings

logger = logging.getLogger("gitcompass.ai_service")


# ── Exceptions ─────────────────────────────────────────────────────────────

class QualifyingProviderError(Exception):
    """Base exception for provider-level infrastructure/quota failures that trigger fallback."""
    pass

class RateLimitError(QualifyingProviderError): pass
class QuotaExhaustedError(QualifyingProviderError): pass
class ProviderUnavailableError(QualifyingProviderError): pass
class ProviderTimeoutError(QualifyingProviderError): pass

class AllProvidersFailedError(Exception):
    """Dedicated exception raised when all active providers in the chain fail."""
    pass


# ── Provider Abstraction ───────────────────────────────────────────────────

class AIProvider(ABC):
    name: str

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, str]:
        """
        Returns normalized internal dict: {'text': str, 'provider_name': str}
        Raises QualifyingProviderError only on explicit network failures or empty responses.
        """
        pass


class GeminiProvider(AIProvider):
    def __init__(self, model_name: str):
        self.name = f"gemini ({model_name})"
        self.model_name = model_name
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Dict[str, str]:
        prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature)
            )
            text = response.text
            if not text:
                raise ProviderUnavailableError("Gemini returned empty/null response.")
            return {"text": text, "provider_name": self.name}
        except APIError as exc:
            # Classify Gemini API errors
            error_msg = str(exc).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                raise RateLimitError(f"Gemini Rate Limit: {exc}")
            if "quota" in error_msg:
                raise QuotaExhaustedError(f"Gemini Quota Exhausted: {exc}")
            if "503" in error_msg or "unavailable" in error_msg:
                raise ProviderUnavailableError(f"Gemini Unavailable: {exc}")
            # Other APIErrors (like 500s or transport) are generally unavailability
            raise ProviderUnavailableError(f"Gemini Error: {exc}")
        except QualifyingProviderError:
            raise
        except Exception as exc:
            # Let other exceptions (like malformed requests) bubble up
            raise ProviderUnavailableError(f"Gemini Unexpected Transport/API Error: {exc}")


class GroqProvider(AIProvider):
    def __init__(self):
        self.name = "groq"
        self.model_name = settings.GROQ_MODEL
        self.api_key = settings.GROQ_API_KEY
        self.timeout = settings.GROQ_TIMEOUT

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Dict[str, str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                
                if resp.status_code == 429:
                    raise RateLimitError(f"Groq Rate Limit/Quota: {resp.text}")
                elif resp.status_code >= 500:
                    raise ProviderUnavailableError(f"Groq Unavailable ({resp.status_code}): {resp.text}")
                
                resp.raise_for_status()
                data = resp.json()
                
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not text:
                    raise ProviderUnavailableError("Groq returned empty/null response.")
                
                return {"text": text, "provider_name": self.name}
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Groq Timeout: {exc}")
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Groq Network Error: {exc}")
        except QualifyingProviderError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(f"Groq Unexpected Error: {exc}")


# ── Coordinator & Routing ──────────────────────────────────────────────────

def select_gemini_model(task_type: str) -> str:
    """Routes the task to the appropriate Gemini model."""
    if task_type in ("evolution_summary", "qa"):
        return settings.GEMINI_FLASH_LITE_MODEL
    elif task_type in ("architecture_shifts", "development_story"):
        return settings.GEMINI_FLASH_MODEL
    return settings.GEMINI_FLASH_LITE_MODEL


def build_provider_chain(gemini_model: str, selected_model: str = "auto") -> List[AIProvider]:
    """Builds the ordered list of fallback providers based on explicit selection."""
    providers: List[AIProvider] = []
    
    if selected_model == "groq":
        if settings.GROQ_API_KEY:
            providers.append(GroqProvider())
        return providers

    if selected_model == "gemini_flash":
        model_to_use = settings.GEMINI_FLASH_MODEL
    elif selected_model == "gemini_flash_lite":
        model_to_use = settings.GEMINI_FLASH_LITE_MODEL
    else:
        model_to_use = gemini_model
        
    if settings.GEMINI_API_KEY:
        providers.append(GeminiProvider(model_name=model_to_use))
    
    if settings.GROQ_API_KEY:
        providers.append(GroqProvider())
        
    return providers


async def generate_ai_response(
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    selected_model: str = "auto"
) -> Dict[str, str]:
    """
    Executes the AI request using the task-aware provider fallback chain.
    """
    gemini_model = select_gemini_model(task_type)
    providers = build_provider_chain(gemini_model, selected_model)
    
    if not providers:
        raise AllProvidersFailedError("No AI providers configured or enabled.")

    errors = []
    for provider in providers:
        try:
            logger.info(f"[AI] Task={task_type} Model/Provider={provider.name} request started")
            result = await provider.generate(system_prompt, user_prompt, temperature)
            logger.info(f"[AI] Task={task_type} Provider={provider.name} succeeded")
            return result
        except QualifyingProviderError as exc:
            logger.warning(f"[AI] {provider.name} provider error: {exc}. Attempting fallback...")
            errors.append((provider.name, str(exc)))

    raise AllProvidersFailedError(f"All configured AI providers failed: {errors}")


# ── AI Feature Functions ───────────────────────────────────────────────────

import re

REPOSITORY_INTELLIGENCE_PROMPT = """You are a repository archaeology and software evolution analyst for GitCompass.
You analyze structured, deterministic evidence extracted from a real Git repository.
Your responsibility is to reason over the supplied evidence.
You are NOT responsible for discovering facts that are absent from the evidence.

Rules:
1. Every factual claim must be supported by the supplied evidence.
2. Never invent file names, technologies, dates, contributors, or architectural decisions.
3. Never infer a previous technology merely because a new technology appears.
4. Never claim a migration unless evidence supports both the new and previous state.
5. Never claim developer motivation unless evidence supports it.
6. If motivation or significance is reasonably inferred, label it [INFERENCE].
7. If the evidence is insufficient to explain something, say [UNKNOWN].
8. If the user makes an assumption or statement that contradicts the evidence, explicitly correct them.
9. Prefer concrete repository entities over generic language.
10. Prefer specific files, directories, technologies, phases, and dates.
11. Do not repeat statistics without explaining their engineering significance.
12. Do not produce generic statements that could describe any repository.
13. Do not invent causal relationships between unrelated events.
14. Treat Stage 5 and Stage 6 deterministic data as authoritative.
15. Stage 6 phase boundaries must never be changed by you.
16. If large_change events exist without clear architectural meaning, do not invent an explanation; state [UNKNOWN].
"""

def _extract_json(text: str, is_array: bool = False) -> str:
    """Robustly extract JSON from model output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    if is_array:
        match = re.search(r'\[.*\]', text, re.DOTALL)
    else:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
    if match:
        return match.group(0)
    return text


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
        text = _extract_json(result["text"], is_array=False)
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
    if not phases:
        raise ValueError("No architecture phases found for this repository. Ensure it has been fully mined and contains significant events.")

    compact_evidence = json.dumps({
        "repository": evidence.get("repository"),
        "technology": evidence.get("technology"),
        "phases": phases
    }, separators=(',', ':'))

    system_prompt = REPOSITORY_INTELLIGENCE_PROMPT
    user_prompt = f"""You are analyzing the architectural evolution of the repository '{repo_name}'.
You are receiving deterministic architectural phases extracted by a static analysis engine.
Phase boundaries are authoritative. Do not invent dates or phases that are not present in the evidence.

Evidence (JSON):
{compact_evidence}

Synthesize these deterministic phases into a chronological timeline of architectural shifts.
Return a JSON array of objects. Each object must have exactly these keys:
{{
  "date": "YYYY-MM-DD (must use the phase start_date)",
  "title": "Short architectural label",
  "what_changed": "Concrete facts supported by evidence.",
  "architectural_significance": "Why this matters. Use [INFERENCE] when interpretation is involved.",
  "evidence_items": [
    "String items directly from the evidence (e.g. 'dependency_added: fastapi')"
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
        text = _extract_json(result["text"], is_array=True)
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


async def answer_qa(repo_name: str, history: List[Dict[str, str]], evidence: dict, selected_model: str = "auto") -> str:
    """Answers a Q&A question using the repository evidence and conversation history."""
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

CONVERSATION HISTORY:
{history_str if history_str else "No previous history."}

CURRENT QUESTION:
{current_question}

Answer directly based ONLY on the available repository evidence.
If `evidence_status` is "unavailable", you MUST explicitly state that repository evidence could not be retrieved and refuse to answer repository-specific questions.
If the evidence doesn't support a definitive answer, clearly state that the evidence does not establish it. DO NOT fabricate historical reasons, file names, or architectural choices. Distinguish clearly between concrete facts and your own inferences. Keep your answer concise, technical, and use markdown for readability.
"""
    try:
        result = await generate_ai_response(
            task_type="qa",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            selected_model=selected_model
        )
        return result["text"]
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for Q&A: {exc}")
        return f"AI Analysis Unavailable: {exc}"
    except Exception as exc:
        logger.error(f"Failed to answer question: {exc}")
        return f"Failed to answer question: {exc}"


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
        text = _extract_json(result["text"], is_array=False)
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




