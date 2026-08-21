import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid

from app.main import app
from app.dependencies import get_current_user, get_db

@pytest.fixture
def test_client():
    test_user_id = str(uuid.uuid4())

    async def mock_get_current_user():
        return {
            "sub": test_user_id,
            "email": "testuser@example.com",
            "role": "authenticated",
        }

    mock_db = MagicMock()
    # Mock repository authorization to succeed
    mock_db.table().select().eq().execute.return_value.data = [
        {"name": "test-repo", "total_commits": 10, "latest_commit_sha": "abc1234"}
    ]

    async def mock_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    yield TestClient(app), mock_db

    app.dependency_overrides.clear()


@patch("app.routers.ai.assemble_evidence")
@patch("app.routers.ai.generate_evolution_summary")
def test_get_ai_summary_success(mock_generate, mock_assemble, test_client):
    client, mock_db = test_client
    
    mock_assemble.return_value = {"mock": "evidence"}
    mock_generate.return_value = {"what_is_this": "test"}
    
    res = client.post("/api/ai/summary/repo_123", json={"force_refresh": True})
    
    assert res.status_code == 200
    assert res.json() == {"summary": {"what_is_this": "test"}, "is_cached": False, "is_stale": False}
    
    mock_assemble.assert_called_once_with("repo_123", mock_db)
    mock_generate.assert_called_once()
    assert mock_generate.call_args[1]["evidence"] == {"mock": "evidence"}

@patch("app.routers.ai.assemble_evidence")
@patch("app.routers.ai.detect_architecture_shifts")
def test_get_architecture_shifts_success(mock_detect, mock_assemble, test_client):
    client, mock_db = test_client
    
    mock_assemble.return_value = {"mock": "evidence"}
    mock_detect.return_value = [{"date": "2026-01-01", "title": "test shift"}]
    
    res = client.post("/api/ai/shifts/repo_123", json={"force_refresh": True})
    
    assert res.status_code == 200
    assert res.json() == {"shifts": [{"date": "2026-01-01", "title": "test shift"}]}
    
    mock_assemble.assert_called_once_with("repo_123", mock_db)
    mock_detect.assert_called_once()
    assert mock_detect.call_args[1]["evidence"] == {"mock": "evidence"}

@patch("app.routers.ai.assemble_evidence")
@patch("app.routers.ai.generate_development_story")
def test_get_development_story_success(mock_generate, mock_assemble, test_client):
    client, mock_db = test_client
    
    mock_assemble.return_value = {"mock": "evidence"}
    mock_generate.return_value = {"overall_arc": "test arc"}
    
    res = client.post("/api/ai/story/repo_123", json={"force_refresh": True})
    
    assert res.status_code == 200
    assert res.json() == {"story": {"overall_arc": "test arc"}}
    
    mock_assemble.assert_called_once_with("repo_123", mock_db)
    mock_generate.assert_called_once()
    assert mock_generate.call_args[1]["evidence"] == {"mock": "evidence"}

def test_unauthorized_repository_access(test_client):
    client, mock_db = test_client
    # Simulate DB returning empty for repo query (Not found / unauthorized via RLS)
    mock_db.table().select().eq().execute.return_value.data = []
    
    res = client.post("/api/ai/summary/repo_123", json={"force_refresh": True})
    
    assert res.status_code == 404
    assert res.json()["detail"] == "Repository not found"
