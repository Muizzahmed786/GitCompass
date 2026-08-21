import unittest
from unittest.mock import patch, MagicMock
import json

from app.services.ai_service import (
    generate_evolution_summary,
    detect_architecture_shifts,
    generate_development_story,
    REPOSITORY_INTELLIGENCE_PROMPT,
    _extract_json
)

class TestAIServicePrompts(unittest.TestCase):
    def test_system_prompt_exists(self):
        """Test 1: System prompts exist and are not empty."""
        self.assertTrue(len(REPOSITORY_INTELLIGENCE_PROMPT) > 0)
        self.assertIn("You are a repository archaeology", REPOSITORY_INTELLIGENCE_PROMPT)
        
    def test_fact_inference_rules(self):
        """Test 2: Fact/inference rules exist in the prompt."""
        prompt = REPOSITORY_INTELLIGENCE_PROMPT
        self.assertIn("Every factual claim must be supported by the supplied evidence", prompt)
        self.assertIn("[INFERENCE]", prompt)
        self.assertIn("[UNKNOWN]", prompt)
        
    def test_no_hallucination_instructions(self):
        """Test 7: No hallucination instructions are explicitly stated."""
        prompt = REPOSITORY_INTELLIGENCE_PROMPT
        self.assertIn("Never invent file names, technologies, dates", prompt)
        self.assertIn("Never infer a previous technology merely because a new technology appears", prompt)
        self.assertIn("Never claim a migration unless evidence supports both", prompt)
        self.assertIn("Never claim developer motivation", prompt)
        
    def test_extract_json_valid_object(self):
        """Test 6a: JSON parsing extracts valid object correctly."""
        raw = "```json\n{\n  \"key\": \"value\"\n}\n```"
        extracted = _extract_json(raw, is_array=False)
        self.assertEqual(json.loads(extracted), {"key": "value"})
        
    def test_extract_json_valid_array(self):
        """Test 6b: JSON parsing extracts valid array correctly."""
        raw = "Here is your response:\n```json\n[\n  {\"key\": \"value\"}\n]\n```\nEnjoy!"
        extracted = _extract_json(raw, is_array=True)
        self.assertEqual(json.loads(extracted), [{"key": "value"}])

class TestAIServiceFunctions(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_evidence = {
            "repository": {"name": "test-repo"},
            "phases": [{"title": "Phase 1", "start_date": "2026-01-01"}]
        }

    @patch("app.services.ai_service.generate_ai_response")
    async def test_development_story_schema(self, mock_generate):
        """Test 3: Development Story schema enforcement."""
        mock_generate.return_value = {
            "text": '{"phases": [{"title": "P1", "period": "2026", "narrative": "abc", "key_files": [], "key_technologies": [], "key_contributors": [], "significance": "FACT"}], "overall_arc": "xyz"}'
        }
        
        result = await generate_development_story("test-repo", self.mock_evidence)
        self.assertIn("phases", result)
        self.assertIn("overall_arc", result)
        
        # Check prompt args
        args, kwargs = mock_generate.call_args
        user_prompt = kwargs["user_prompt"]
        self.assertIn('"title": "Use the Stage 6 phase title"', user_prompt)
        self.assertIn('"period": "YYYY-MM-DD to YYYY-MM-DD (from Stage 6)"', user_prompt)
        self.assertIn('"narrative":', user_prompt)
        self.assertIn('"key_files":', user_prompt)
        self.assertIn('"key_technologies":', user_prompt)
        self.assertIn('"key_contributors":', user_prompt)
        self.assertIn('"significance":', user_prompt)

    @patch("app.services.ai_service.generate_ai_response")
    async def test_architecture_timeline_schema(self, mock_generate):
        """Test 4: Architecture Timeline schema enforcement."""
        mock_generate.return_value = {
            "text": '[{"date": "2026", "title": "abc", "what_changed": "def", "architectural_significance": "ghi", "evidence_items": []}]'
        }
        
        result = await detect_architecture_shifts("test-repo", self.mock_evidence)
        self.assertTrue(isinstance(result, list))
        self.assertIn("date", result[0])
        
        # Check prompt args
        args, kwargs = mock_generate.call_args
        user_prompt = kwargs["user_prompt"]
        self.assertIn('"date": "YYYY-MM-DD', user_prompt)
        self.assertIn('"title":', user_prompt)
        self.assertIn('"what_changed":', user_prompt)
        self.assertIn('"architectural_significance":', user_prompt)
        self.assertIn('"evidence_items":', user_prompt)
        
    @patch("app.services.ai_service.generate_ai_response")
    async def test_evolution_summary_schema(self, mock_generate):
        """Test 5: AI Summary schema enforcement."""
        mock_generate.return_value = {
            "text": '{"what_is_this": "abc", "technology_stack": {}, "architecture_overview": "def", "evolution_summary": "ghi", "key_areas": [], "onboarding_notes": "jkl"}'
        }
        
        result = await generate_evolution_summary("test-repo", self.mock_evidence)
        self.assertIn("what_is_this", result)
        self.assertIn("technology_stack", result)
        
        # Check prompt args
        args, kwargs = mock_generate.call_args
        user_prompt = kwargs["user_prompt"]
        self.assertIn('"what_is_this":', user_prompt)
        self.assertIn('"technology_stack":', user_prompt)
        self.assertIn('"architecture_overview":', user_prompt)
        self.assertIn('"evolution_summary":', user_prompt)
        self.assertIn('"key_areas":', user_prompt)
        self.assertIn('"onboarding_notes":', user_prompt)

    @patch("app.services.ai_service.generate_ai_response")
    async def test_malformed_json_raises_value_error(self, mock_generate):
        """Test 6c: Malformed JSON triggers ValueError."""
        mock_generate.return_value = {"text": "I am not JSON at all."}
        
        with self.assertRaises(ValueError) as ctx:
            await generate_evolution_summary("test-repo", self.mock_evidence)
        
        self.assertIn("Failed to parse evolution summary", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
