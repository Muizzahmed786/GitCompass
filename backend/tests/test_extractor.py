"""
Unit test for git log extractor parsing logic.
Tests rename pattern resolution, numstat line parsing, and date parsing.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

from app.services.cloner import parse_github_url
from app.services.extractor import extract_git_history, parse_git_path


class TestExtractor(unittest.TestCase):
    def test_parse_github_url(self):
        url1 = "https://github.com/fastapi/fastapi"
        owner, repo = parse_github_url(url1)
        self.assertEqual(owner, "fastapi")
        self.assertEqual(repo, "fastapi")

        url2 = "https://github.com/octocat/Hello-World.git"
        owner, repo = parse_github_url(url2)
        self.assertEqual(owner, "octocat")
        self.assertEqual(repo, "Hello-World")

        url3 = "git@github.com:facebook/react.git"
        owner, repo = parse_github_url(url3)
        self.assertEqual(owner, "facebook")
        self.assertEqual(repo, "react")

    def test_parse_git_path_simple(self):
        cur, old, is_ren = parse_git_path("src/index.js")
        self.assertEqual(cur, "src/index.js")
        self.assertIsNone(old)
        self.assertFalse(is_ren)

    def test_parse_git_path_renames(self):
        # Direct rename
        cur, old, is_ren = parse_git_path("old.js => new.js")
        self.assertEqual(cur, "new.js")
        self.assertEqual(old, "old.js")
        self.assertTrue(is_ren)

        # Subdirectory brace rename
        cur, old, is_ren = parse_git_path("src/{utils => lib}/helper.js")
        self.assertEqual(cur, "src/lib/helper.js")
        self.assertEqual(old, "src/utils/helper.js")
        self.assertTrue(is_ren)

        # Prefix brace rename
        cur, old, is_ren = parse_git_path("{old_dir => new_dir}/file.txt")
        self.assertEqual(cur, "new_dir/file.txt")
        self.assertEqual(old, "old_dir/file.txt")
        self.assertTrue(is_ren)

    def test_extract_git_history_on_local_repo(self):
        temp_dir = tempfile.mkdtemp(prefix="test_git_repo_")
        try:
            # Create a real mini git repository
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.name", "Test Author"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)

            # Commit 1: Add main.py
            file1 = os.path.join(temp_dir, "main.py")
            with open(file1, "w") as f:
                f.write("print('hello world')\n")
            subprocess.run(["git", "add", "main.py"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

            # Commit 2: Rename main.py to app.py and add utils.py
            file2 = os.path.join(temp_dir, "app.py")
            os.rename(file1, file2)
            file3 = os.path.join(temp_dir, "utils.py")
            with open(file3, "w") as f:
                f.write("def add(a, b):\n    return a + b\n")

            subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Refactor and add utils"], cwd=temp_dir, check=True)

            # Extract history using extractor
            commits, file_diffs, total_commits, total_files = extract_git_history(
                temp_dir, "test_repo_id", "test_user_id"
            )

            self.assertEqual(total_commits, 2)
            self.assertGreaterEqual(total_files, 2)
            self.assertEqual(len(commits), 2)
            self.assertGreaterEqual(len(file_diffs), 3)

            # Verify rename was detected in file_diffs
            rename_diffs = [d for d in file_diffs if d["is_rename"]]
            self.assertTrue(len(rename_diffs) > 0)
            self.assertEqual(rename_diffs[0]["file_path"], "app.py")
            self.assertEqual(rename_diffs[0]["old_path"], "main.py")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
