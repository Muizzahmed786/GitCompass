"""
AI Prompts Service.

Contains the base system prompts and JSON extraction utilities.
"""

import json

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

def extract_json(text: str, is_array: bool = False) -> str:
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
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
    else:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
            
    return text
