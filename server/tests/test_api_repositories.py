"""
Integration test for repository creation and background mining.
"""

from datetime import datetime, timezone
import logging
import os
import time
import unittest
import uuid

from fastapi.testclient import TestClient
import jwt

from app.config import settings
from app.main import app

logging.basicConfig(level=logging.INFO)


class TestRepositoryAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_user_id = str(uuid.uuid4())

        from app.dependencies import get_current_user
        
        async def mock_get_current_user():
            return {
                "sub": cls.test_user_id,
                "email": "testuser@example.com",
                "role": "authenticated",
            }

        app.dependency_overrides[get_current_user] = mock_get_current_user
        cls.headers = {"Authorization": "Bearer fake_test_token"}

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_health_auth(self):
        res = self.client.get("/api/health/auth", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user_id"], self.test_user_id)

    def test_invalid_github_url(self):
        res = self.client.post(
            "/api/repositories",
            json={"github_url": "https://notgithub.com/foo/bar"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 422)  # Pydantic validation error


if __name__ == "__main__":
    unittest.main()
