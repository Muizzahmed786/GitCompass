import unittest
from unittest.mock import patch, MagicMock
from app.services.evolution_analyzer import (
    analyze_evolution, analyze_dependencies_for_commit, get_commit_parents, directory_exists_at_commit
)
from datetime import datetime, timezone
import uuid

class TestEvolutionAnalyzer(unittest.TestCase):
    
    @patch('app.services.evolution_analyzer.subprocess.run')
    def test_get_commit_parents_single(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "parent_sha_1\n"
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        parents = get_commit_parents("/tmp", "commit_sha")
        self.assertEqual(parents, ["parent_sha_1"])
        
    @patch('app.services.evolution_analyzer.subprocess.run')
    def test_get_commit_parents_merge(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "parent_1 parent_2\n"
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        parents = get_commit_parents("/tmp", "commit_sha")
        self.assertEqual(parents, ["parent_1", "parent_2"])
        
    @patch('app.services.evolution_analyzer.subprocess.run')
    def test_directory_exists_at_commit(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "040000 tree 1234\tdir\n"
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        self.assertTrue(directory_exists_at_commit("/tmp", "sha", "dir"))
        
        mock_proc.stdout = ""
        self.assertFalse(directory_exists_at_commit("/tmp", "sha", "dir"))
        
        self.assertFalse(directory_exists_at_commit("/tmp", None, "dir"))
        
    @patch('app.services.evolution_analyzer.get_commit_parents')
    @patch('app.services.evolution_analyzer.get_file_content_at_commit')
    def test_analyze_dependencies_added_removed_changed(self, mock_get_content, mock_get_parents):
        mock_get_parents.return_value = ["parent_sha"]
        
        # Parent commit has redis 4.0, express 4.17, lodash 4.0
        parent_json = '{"dependencies": {"redis": "4.0", "express": "4.17.1", "lodash": "4.0"}}'
        # Current commit has redis 4.7.0 (changed), react 18.0 (added), express is gone (removed), lodash 4.0 (unchanged)
        current_json = '{"dependencies": {"redis": "4.7.0", "react": "18.0.0", "lodash": "4.0"}}'
        
        def mock_content_side_effect(repo, sha, path):
            if sha == "parent_sha": return parent_json
            if sha == "current_sha": return current_json
            return None
            
        mock_get_content.side_effect = mock_content_side_effect
        
        commit = {"sha": "current_sha"}
        file_diffs = [{"file_path": "package.json", "old_path": None}]
        
        events = analyze_dependencies_for_commit("/tmp", commit, file_diffs)
        event_types = {e["event_type"]: e for e in events}
        
        self.assertIn("dependency_added", event_types)
        self.assertEqual(event_types["dependency_added"]["metadata"]["dependency"], "react")
        
        self.assertIn("dependency_version_changed", event_types)
        self.assertEqual(event_types["dependency_version_changed"]["metadata"]["dependency"], "redis")
        
        self.assertIn("dependency_removed", event_types)
        self.assertEqual(event_types["dependency_removed"]["metadata"]["dependency"], "express")
        
        # Ensure lodash didn't trigger an event
        for e in events:
            self.assertNotEqual(e["metadata"]["dependency"], "lodash")

    @patch('app.services.evolution_analyzer.get_commit_parents')
    @patch('app.services.evolution_analyzer.get_file_content_at_commit')
    def test_analyze_dependencies_malformed(self, mock_get_content, mock_get_parents):
        mock_get_parents.return_value = ["parent_sha"]
        parent_json = '{"dependencies": {"redis": "4.0"}}'
        current_json = 'MALFORMED JSON {' # Should fail to parse gracefully
        
        def mock_content_side_effect(repo, sha, path):
            if sha == "parent_sha": return parent_json
            if sha == "current_sha": return current_json
            return None
            
        mock_get_content.side_effect = mock_content_side_effect
        commit = {"sha": "current_sha"}
        file_diffs = [{"file_path": "package.json", "old_path": None}]
        
        events = analyze_dependencies_for_commit("/tmp", commit, file_diffs)
        # Because after state is empty (failed to parse), it assumes redis was removed
        event_types = {e["event_type"]: e for e in events}
        self.assertIn("dependency_removed", event_types)
        
    @patch('app.services.evolution_analyzer.get_service_client')
    @patch('app.services.evolution_analyzer.analyze_dependencies_for_commit')
    @patch('app.services.evolution_analyzer.directory_exists_at_commit')
    def test_analyze_evolution_structural_and_incremental(self, mock_dir_exists, mock_dep, mock_db):
        mock_dep.return_value = []
        mock_db_client = MagicMock()
        mock_db.return_value = mock_db_client
        
        # c1 introduces src/services/auth.
        # c2 modifies src/services/auth, but it already existed (incremental sync scenario where c1 is not in list but we mock dir_exists)
        
        commits = [
            {"id": "commit_2", "sha": "c2", "committed_at": "2024-02-01", "message": "refactor(auth): big rewrite", "insertions": 15000, "deletions": 500},
            {"id": "commit_1b", "sha": "c1b", "committed_at": "2024-01-15", "message": "refactoring some text", "insertions": 50, "deletions": 10},
        ]
        for i in range(20):
            commits.append({"id": f"commit_small_{i}", "sha": f"c_{i}", "committed_at": f"2024-01-1{i}", "message": "feat: minor", "insertions": 50, "deletions": 10})
        
        commits.append({"id": "commit_1", "sha": "c1", "committed_at": "2024-01-01", "message": "feat: initial commit", "insertions": 100, "deletions": 0})
        
        file_diffs = [
            {"commit_id": "commit_1", "file_path": "package.json"},
            {"commit_id": "commit_1", "file_path": "src/services/auth/login.py"},
            {"commit_id": "commit_1", "file_path": "src/services/auth/token.py"},
            {"commit_id": "commit_2", "file_path": "src/services/auth/login.py"},
            {"commit_id": "commit_2", "file_path": "src/services/db/connection.py"} # New dir
        ]
        
        def mock_dir_exists_impl(repo, sha, path):
            # src/services/db didn't exist before c2.
            if path == "src/services/db": return False
            # During processing of c1, parent is None (so it correctly doesn't call this or returns False).
            # But let's just say anything else existed if sha is c2's parent
            return True
            
        mock_dir_exists.side_effect = mock_dir_exists_impl
        
        inserted_events = []
        def mock_upsert(chunk, on_conflict=None):
            inserted_events.extend(chunk)
            mock_execute = MagicMock()
            return mock_execute
            
        mock_db_client.table().upsert = mock_upsert
        
        analyze_evolution("repo_1", "/tmp", commits, file_diffs)
        
        events_by_type = {}
        for e in inserted_events:
            events_by_type.setdefault(e["event_type"], []).append(e)
            
        self.assertIn("manifest_introduced", events_by_type)
        
        # Directory introduced should contain src/services/auth (from c1) and src/services/db (from c2)
        dirs_introduced = [e["metadata"]["directory_path"] for e in events_by_type.get("directory_introduced", [])]
        self.assertIn("src/services/auth", dirs_introduced)
        self.assertIn("src/services/db", dirs_introduced)
        
        self.assertIn("large_change", events_by_type)
        self.assertEqual(events_by_type["large_change"][0]["commit_id"], "commit_2")
        
        # c2 is a real refactor. c1b has "refactoring" but is NOT a conventional commit.
        refactors = events_by_type.get("commit_declared_refactor", [])
        self.assertEqual(len(refactors), 1)
        self.assertEqual(refactors[0]["commit_id"], "commit_2")
        
if __name__ == '__main__':
    unittest.main()
