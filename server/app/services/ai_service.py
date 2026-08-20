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

async def generate_evolution_summary(repo_name: str, aggregated_data: dict, selected_model: str = "auto") -> str:
    """Generates a concise developer-focused summary of the repository from aggregated JSON data."""
    compact_json = json.dumps(aggregated_data, separators=(',', ':'))

    system_prompt = ""
    user_prompt = f"""You are analyzing a software repository called '{repo_name}' based on its Git history metrics.

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
        result = await generate_ai_response(
            task_type="evolution_summary",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            selected_model=selected_model
        )
        return result["text"]
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for summary: {exc}")
        return f"AI Analysis Unavailable: {exc}"
    except Exception as exc:
        logger.error(f"Failed to generate AI summary: {exc}")
        return f"Failed to generate AI summary: {exc}"


async def detect_architecture_shifts(repo_name: str, total_commits: int, structured_phases: List[Dict], selected_model: str = "auto") -> List[Dict]:
    """
    Detects major architectural shifts from deterministic phases (Stage 6).
    Limits processing to repositories with <= MAX_COMMITS_FOR_SHIFT_DETECTION.
    """
    if total_commits > settings.MAX_COMMITS_FOR_SHIFT_DETECTION:
        raise ValueError(
            f"This repository has {total_commits} commits, which exceeds the {settings.MAX_COMMITS_FOR_SHIFT_DETECTION}-commit limit for shift detection. "
            f"This limit exists to control token usage. You can raise it in config if needed."
        )

    if not structured_phases:
        raise ValueError("No architecture phases found for this repository. Ensure it has been fully mined and contains significant events.")

    phases_json = json.dumps(structured_phases, indent=2, default=str)

    system_prompt = ""
    user_prompt = f"""You are analyzing the architectural evolution of the repository '{repo_name}'.

Instead of raw commits, you are receiving deterministic architectural phases extracted by a static analysis engine. 
Each phase contains hard evidence (such as framework dependencies added or directories created).

Phase Data (JSON):
{phases_json}

Synthesize these deterministic phases into a human-readable timeline of architectural shifts.
Do NOT invent dates or phases that are not present in the data. You are simply translating the structured JSON into a readable narrative.

Return ONLY a valid JSON array. No markdown, no explanation, no conversational filler.
Each object must have exactly these keys:
- "date": "YYYY-MM-DD" (use the start_date of the phase)
- "title": short label (max 8 words) (you can use the phase title directly or polish it slightly)
- "description": one factual sentence explaining what the architectural shift was and what evidence supports it. (IMPORTANT: Properly escape any quotes inside this string).

If you cannot identify clear architectural shifts from the phase data, return an empty array: []
"""
    try:
        result = await generate_ai_response(
            task_type="architecture_shifts",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            selected_model=selected_model
        )
        
        text = result["text"].strip()
        
        import re
        # Robustly extract the JSON array, ignoring conversational filler before or after
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
                
        return json.loads(text)
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for shift detection: {exc}")
        raise ValueError(f"AI Analysis Unavailable: {exc}")
    except json.JSONDecodeError as exc:
        # Feature-level failure (does not trigger fallback)
        logger.error(f"Malformed JSON returned by provider: {exc}")
        raise ValueError(f"Failed to parse architecture shifts from AI response: {exc}")
    except Exception as exc:
        logger.error(f"Failed to detect architectural shifts: {exc}")
        raise ValueError(f"Failed to detect architectural shifts: {exc}")


async def answer_qa(repo_name: str, question: str, context_summary: str, selected_model: str = "auto") -> str:
    """Answers user queries about the repository using context."""
    system_prompt = f"You are a technical assistant for the repository '{repo_name}'."
    
    user_prompt = f"""Repository context (from Git history analysis):
{context_summary}

Developer's question: {question}

Answer directly based on the available data. If the data doesn't support a definitive answer, say so clearly and briefly. 
Keep your answer concise and technical. Use markdown for formatting where it helps readability (e.g. bold file names, code blocks for paths).
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


async def generate_development_story(repo_name: str, timeline_data: dict, selected_model: str = "auto") -> str:
    """Generates a non-technical, chronological story retelling how the repository evolved over time."""
    compact_json = json.dumps(timeline_data, separators=(',', ':'))

    system_prompt = ""
    user_prompt = f"""You are telling the development story of the repository '{repo_name}' based on its chronological Git history summary.

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
        result = await generate_ai_response(
            task_type="development_story",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            selected_model=selected_model
        )
        return result["text"]
    except AllProvidersFailedError as exc:
        logger.error(f"All AI providers failed for development story: {exc}")
        return f"AI Analysis Unavailable: {exc}"
    except Exception as exc:
        logger.error(f"Failed to generate development story: {exc}")
        return f"Failed to generate development story: {exc}"



