from typing import Dict, List
from pydantic import BaseModel, Field

class FrameworkEvidence(BaseModel):
    name: str
    evidence: List[str] = Field(default_factory=list)

class CiCdConfig(BaseModel):
    platform: str
    path: str

class Directories(BaseModel):
    source: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    config: List[str] = Field(default_factory=list)
    documentation: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)

class Statistics(BaseModel):
    totalFiles: int = 0
    codeFiles: int = 0
    testFiles: int = 0

class RepositoryStructure(BaseModel):
    languages: Dict[str, int] = Field(default_factory=dict)
    frameworks: List[FrameworkEvidence] = Field(default_factory=list)
    buildTools: List[str] = Field(default_factory=list)
    packageManagers: List[str] = Field(default_factory=list)
    directories: Directories = Field(default_factory=Directories)
    configurationFiles: List[str] = Field(default_factory=list)
    ciCd: List[CiCdConfig] = Field(default_factory=list)
    metadataFiles: List[str] = Field(default_factory=list)
    manifestFiles: List[str] = Field(default_factory=list)
    sourceFiles: List[str] = Field(default_factory=list)
    statistics: Statistics = Field(default_factory=Statistics)
