from typing import List, Optional
from pydantic import BaseModel, Field

class Dependency(BaseModel):
    name: str
    version: Optional[str] = None
    ecosystem: str
    category: str
    evidence_path: str

class RepositoryDependencies(BaseModel):
    dependencies: List[Dependency] = Field(default_factory=list)
