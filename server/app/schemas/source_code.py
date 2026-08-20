from typing import List, Optional
from pydantic import BaseModel, Field

class ImportDef(BaseModel):
    source: str
    names: List[str]
    aliases: List[str]

class FunctionDef(BaseModel):
    name: str
    start_line: int
    end_line: int
    is_async: bool
    parameters: List[str]
    decorators: List[str]

class ClassDef(BaseModel):
    name: str
    start_line: int
    end_line: int
    base_classes: List[str]
    methods: List[FunctionDef]

class FileAST(BaseModel):
    file_path: str
    language: str
    imports: List[ImportDef] = Field(default_factory=list)
    classes: List[ClassDef] = Field(default_factory=list)
    functions: List[FunctionDef] = Field(default_factory=list)

class RepositorySourceCode(BaseModel):
    files: List[FileAST] = Field(default_factory=list)
