"""
Pydantic schemas for analytics endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class HotspotResponse(BaseModel):
    file_path: str
    commits_count: int
    total_insertions: int
    total_deletions: int
    authors: List[str]
    is_deleted: bool
    commit_types: Dict[str, int] = {}
    top_author: Optional[str] = None
    top_author_share: float = 0.0
    is_orphan_risk: bool = False


class TemporalCouplingItem(BaseModel):
    file_a: str
    file_b: str
    co_changes: int
    degree: float


class BusFactorResponse(BaseModel):
    repo_bus_factor: int
    top_contributors: Dict[str, int]
    orphan_risk_files: List[dict]


class SummaryAnalyticsResponse(BaseModel):
    total_commits: int
    total_files: int
    bus_factor: int
    commit_types_distribution: Dict[str, int]
    total_coupled_pairs: int
    orphan_files_count: int


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    category: Optional[str] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    is_truncated: bool = False
