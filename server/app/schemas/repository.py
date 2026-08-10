"""
Pydantic schemas for Repository resources.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re


class RepositoryCreate(BaseModel):
    github_url: str = Field(
        ...,
        description="Public GitHub repository URL (e.g. https://github.com/owner/repo)",
        example="https://github.com/fastapi/fastapi",
    )
    branch: Optional[str] = Field(
        None,
        description="Optional branch to mine. Defaults to the repository's default branch if omitted.",
        example="main",
    )

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        # Accept forms like:
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        pattern = r"^(https?://github\.com/|git@github\.com:)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$/?"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid GitHub URL. Must be a valid GitHub repository link (e.g. https://github.com/owner/repo)"
            )
        return v


class RepositoryResponse(BaseModel):
    id: str
    user_id: str
    github_url: str
    name: Optional[str] = None
    default_branch: str = "main"
    status: str
    error_message: Optional[str] = None
    mining_progress: Optional[int] = 0
    total_commits: int = 0
    total_files: int = 0
    latest_commit_sha: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]
    count: int
