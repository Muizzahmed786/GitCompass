"""
AI Providers Service.

Defines the abstract AI provider interface and implementations (Gemini, Groq).
Manages provider instantiation, API client wrappers, and error normalization.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List

import httpx
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from google.genai.errors import APIError

from app.config import settings

logger = logging.getLogger("gitcompass.services.ai_providers")

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
