import unittest
from unittest.mock import patch, MagicMock
from app.services.miner import mine_repository_task

class TestMinerStage5Isolation(unittest.TestCase):
    @patch("app.services.miner.safe_cleanup_dir")
    @patch("app.services.miner.analyze_phases")
    @patch("app.services.miner.analyze_evolution")
    @patch("app.services.miner.replace_knowledge_model")
    @patch("app.services.miner.analyze_source_code")
    @patch("app.services.miner.analyze_dependencies")
    @patch("app.services.miner.analyze_repository_structure")
    @patch("app.services.miner.batch_insert")
    @patch("app.services.miner.extract_git_history")
    @patch("app.services.miner.clone_repository")
    @patch("app.services.miner.tempfile.mkdtemp")
    @patch("app.services.miner.get_service_client")
    def test_stage_5_failure_isolation(
        self,
        mock_get_service_client,
        mock_mkdtemp,
        mock_clone,
        mock_extract,
        mock_batch,
        mock_structure,
        mock_deps,
        mock_source,
        mock_knowledge,
        mock_evolution,
        mock_phases,
        mock_cleanup
    ):
        # 1. Setup mocks
        mock_db = MagicMock()
        mock_get_service_client.return_value = mock_db
        
        # Track update calls
        update_calls = []
        mock_update = MagicMock()
        mock_db.table().update = mock_update
        def side_effect_update(payload):
            update_calls.append(payload)
            mock_eq = MagicMock()
            mock_eq.eq().execute.return_value = None
            return mock_eq
        mock_update.side_effect = side_effect_update

        mock_mkdtemp.return_value = "/tmp/dummy_repo"
        
        # Return valid git history to trigger Stages 1-5
        mock_extract.return_value = ([], [], 10, 5, "dummy_latest_sha")
        
        # 2. Mock analyze_evolution to raise an exception
        mock_evolution.side_effect = Exception("Stage 5 failed horribly")

        # 3. Execute
        mine_repository_task("repo_123", "https://github.com/test/test", "user_123")

        # 4. Verify exception didn't propagate (since the function returned normally)
        # 5. Verify cleanup was still called
        mock_cleanup.assert_called_once_with("/tmp/dummy_repo")

        # 6. Verify the final status update is "ready"
        final_update = update_calls[-1]
        self.assertEqual(final_update["status"], "ready")
        self.assertIsNone(final_update["error_message"])

if __name__ == "__main__":
    unittest.main()
