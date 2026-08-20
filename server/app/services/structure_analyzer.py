import os
import json
from pathlib import Path
from typing import Dict, List, Set, Optional

from app.schemas.structure import (
    RepositoryStructure,
    FrameworkEvidence,
    CiCdConfig,
    Directories,
    Statistics,
)

# Constants for detection
IGNORED_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules",
    "__pycache__", "target", "build", "dist", ".next", "coverage"
}

CI_CD_DIRS = {
    ".github": "GitHub Actions",
    ".gitlab": "GitLab CI",
    ".circleci": "CircleCI"
}

CI_CD_FILES = {
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
    ".travis.yml": "Travis CI",
    "azure-pipelines.yml": "Azure Pipelines"
}

LANGUAGE_EXTENSIONS = {
    ".java": "Java",
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".m": "Objective-C"
}

CODE_LANGUAGES = {
    "Java", "Python", "JavaScript", "TypeScript", "Go", "Rust", 
    "C++", "C", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "Objective-C"
}

BUILD_TOOLS = {
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "settings.gradle": "Gradle",
    "settings.gradle.kts": "Gradle",
    "Makefile": "Make",
    "Cargo.toml": "Cargo"
}

PACKAGE_MANAGERS = {
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "requirements.txt": "pip",
    "pyproject.toml": "pip/poetry",
    "Pipfile": "pipenv",
    "go.mod": "go modules",
    "composer.json": "composer"
}

CONFIG_PATTERNS = [
    ".env.example", "application.yml", "application.properties",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    "nginx.conf", "tsconfig.json", "vite.config", "next.config"
]

METADATA_FILES = {
    "README.md", "README", "LICENSE", ".gitignore", "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile"
}

def _get_top_level_match(current_parts: tuple, target_names: set) -> Optional[str]:
    """Returns the relative path up to the first part that matches a target name."""
    for i, part in enumerate(current_parts):
        if part in target_names:
            return "/".join(current_parts[:i+1])
    return None

def analyze_repository_structure(repo_path: str) -> RepositoryStructure:
    base_path = Path(repo_path).resolve()
    if not base_path.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
        
    structure = RepositoryStructure()
    
    language_counts: Dict[str, int] = {}
    code_files_count = 0
    test_files_count = 0
    total_files_count = 0
    
    frameworks_evidence: Dict[str, List[str]] = {}
    
    def add_framework(name: str, evidence: str):
        if name not in frameworks_evidence:
            frameworks_evidence[name] = []
        if evidence not in frameworks_evidence[name]:
            frameworks_evidence[name].append(evidence)

    for root, dirs, files in os.walk(base_path):
        current_dir = Path(root)
        
        try:
            rel_dir = current_dir.relative_to(base_path).as_posix()
        except ValueError:
            continue
            
        if rel_dir == ".":
            rel_dir = ""
            parts = ()
        else:
            parts = current_dir.relative_to(base_path).parts
            
        # Ignore noisy directories - modify dirs in place to prevent os.walk from traversing
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        
        # Directory categorization (only capture the top-level matching directory to avoid noisy nesting)
        if parts:
            # Test directories
            test_match = _get_top_level_match(parts, {"test", "tests", "__tests__", "spec"})
            if test_match and test_match not in structure.directories.tests:
                structure.directories.tests.append(test_match)
                
            # Source directories
            src_match = _get_top_level_match(parts, {"src", "client", "server", "app", "lib"})
            if src_match and src_match not in structure.directories.source:
                structure.directories.source.append(src_match)
                
            # Documentation
            doc_match = _get_top_level_match(parts, {"docs", "doc"})
            if doc_match and doc_match not in structure.directories.documentation:
                structure.directories.documentation.append(doc_match)
                
            # Config
            cfg_match = _get_top_level_match(parts, {"config", ".config"})
            if cfg_match and cfg_match not in structure.directories.config:
                structure.directories.config.append(cfg_match)
                
            # Infrastructure
            infra_match = _get_top_level_match(parts, {"docker", *CI_CD_DIRS.keys()})
            if infra_match and infra_match not in structure.directories.infrastructure:
                structure.directories.infrastructure.append(infra_match)
                
            # CI/CD Dirs detection
            for part in parts:
                if part in CI_CD_DIRS:
                    platform = CI_CD_DIRS[part]
                    # We just use the first level path where this CI config lives
                    ci_path = _get_top_level_match(parts, {part})
                    if ci_path:
                        # Check if already added
                        if not any(c.path == ci_path for c in structure.ciCd):
                            structure.ciCd.append(CiCdConfig(platform=platform, path=ci_path))

        # Files analysis
        for file in files:
            file_path = current_dir / file
            
            # Skip symlinks or broken files
            if not file_path.is_file():
                continue
                
            rel_file = file_path.relative_to(base_path).as_posix()
            total_files_count += 1
            ext = file_path.suffix.lower()
            
            # 1. Language Detection & Statistics
            is_test_file = False
            if ext in LANGUAGE_EXTENSIONS:
                lang = LANGUAGE_EXTENSIONS[ext]
                language_counts[lang] = language_counts.get(lang, 0) + 1
                
                if lang in CODE_LANGUAGES:
                    code_files_count += 1
                    if rel_file not in structure.sourceFiles:
                        structure.sourceFiles.append(rel_file)
                    
                # Test file detection
                name = file_path.stem.lower()
                test_match = _get_top_level_match(parts, {"test", "tests", "__tests__", "spec"})
                if (
                    "test" in name or 
                    "spec" in name or
                    test_match
                ):
                    test_files_count += 1
                    is_test_file = True

            # 2. Build Tools
            if file in BUILD_TOOLS:
                tool = BUILD_TOOLS[file]
                if tool not in structure.buildTools:
                    structure.buildTools.append(tool)
                if rel_file not in structure.manifestFiles:
                    structure.manifestFiles.append(rel_file)
                    
            # 3. Package Managers
            if file in PACKAGE_MANAGERS:
                pm = PACKAGE_MANAGERS[file]
                if pm not in structure.packageManagers:
                    structure.packageManagers.append(pm)
                if rel_file not in structure.manifestFiles:
                    structure.manifestFiles.append(rel_file)
                    
            # 4. CI/CD Files
            if file in CI_CD_FILES:
                if not any(c.path == rel_file for c in structure.ciCd):
                    structure.ciCd.append(CiCdConfig(platform=CI_CD_FILES[file], path=rel_file))
                
            # 5. Metadata Files
            if file in METADATA_FILES or file.upper().startswith("README"):
                if rel_file not in structure.metadataFiles:
                    structure.metadataFiles.append(rel_file)
                    
            # 6. Configuration Files
            if file == ".env" or any(p in file for p in CONFIG_PATTERNS):
                if rel_file not in structure.configurationFiles:
                    structure.configurationFiles.append(rel_file)
                    
            # 7. Framework Detection (Evidence-based)
            if file == "package.json":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        deps = data.get("dependencies", {})
                        dev_deps = data.get("devDependencies", {})
                        all_deps = {**deps, **dev_deps}
                        
                        if "react" in all_deps:
                            add_framework("React", rel_file)
                        if "next" in all_deps:
                            add_framework("Next.js", rel_file)
                        if "express" in all_deps:
                            add_framework("Express", rel_file)
                        if "vue" in all_deps:
                            add_framework("Vue", rel_file)
                except Exception:
                    pass
                    
            if file == "pom.xml":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "spring-boot" in content:
                            add_framework("Spring Boot", rel_file)
                except Exception:
                    pass
                    
            if file == "requirements.txt" or file == "pyproject.toml":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "fastapi" in content.lower():
                            add_framework("FastAPI", rel_file)
                        if "django" in content.lower():
                            add_framework("Django", rel_file)
                except Exception:
                    pass
                    
            if file == "manage.py":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "django" in content.lower():
                            add_framework("Django", rel_file)
                except Exception:
                    pass

    # Finalize structure
    structure.languages = language_counts
    for fw, ev in frameworks_evidence.items():
        structure.frameworks.append(FrameworkEvidence(name=fw, evidence=ev))
        
    structure.statistics.totalFiles = total_files_count
    structure.statistics.codeFiles = code_files_count
    structure.statistics.testFiles = test_files_count
    
    # Sort them for deterministic output
    structure.buildTools.sort()
    structure.packageManagers.sort()
    structure.configurationFiles.sort()
    structure.metadataFiles.sort()
    structure.manifestFiles.sort()
    structure.sourceFiles.sort()
    
    return structure
