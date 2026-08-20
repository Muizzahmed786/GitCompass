import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
import re
import xml.etree.ElementTree as ET

try:
    import tomllib
except ImportError:
    # Fallback for older python, though Python 3.11+ is expected
    tomllib = None

try:
    import yaml
except ImportError:
    yaml = None

from app.schemas.dependencies import Dependency, RepositoryDependencies

logger = logging.getLogger("gitcompass.dependency_analyzer")

# Simple taxonomies for categorizing dependencies
FRAMEWORKS = {
    "npm": {"react", "next", "vue", "angular", "express", "fastify", "svelte", "nuxt"},
    "pypi": {"django", "fastapi", "flask", "starlette", "tornado"},
}

def _get_category(ecosystem: str, name: str) -> str:
    name_lower = name.lower()
    if ecosystem in FRAMEWORKS and any(fw in name_lower for fw in FRAMEWORKS[ecosystem]):
        return "framework"
    if ecosystem == "maven" and "spring-boot" in name_lower:
        return "framework"
    
    if ecosystem == "docker":
        db_indicators = {"postgres", "mysql", "mariadb", "mongo", "redis", "cassandra"}
        if any(db in name_lower for db in db_indicators):
            return "database"
        return "infrastructure"
        
    return "library"


def parse_package_json(content: str, rel_path: str) -> List[Dependency]:
    deps = []
    try:
        data = json.loads(content)
        for section in ["dependencies", "devDependencies"]:
            for name, version in data.get(section, {}).items():
                deps.append(Dependency(
                    name=name,
                    version=str(version),
                    ecosystem="npm",
                    category=_get_category("npm", name),
                    evidence_path=rel_path
                ))
    except Exception as e:
        logger.warning(f"Failed to parse package.json at {rel_path}: {e}")
    return deps


def parse_requirements_txt(content: str, rel_path: str) -> List[Dependency]:
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        
        # Extremely basic splitting for typical requirements
        match = re.split(r'[=<>~]+', line)
        if match:
            name = match[0].strip()
            # Try to grab version part if it exists
            version = line[len(name):].strip() if len(match) > 1 else None
            if name:
                deps.append(Dependency(
                    name=name,
                    version=version if version else None,
                    ecosystem="pypi",
                    category=_get_category("pypi", name),
                    evidence_path=rel_path
                ))
    return deps


def parse_pyproject_toml(content: str, rel_path: str) -> List[Dependency]:
    deps = []
    if not tomllib:
        logger.warning("tomllib not available, skipping pyproject.toml parsing.")
        return deps
        
    try:
        data = tomllib.loads(content)
        # Check standard PEP 621 dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        for dep_str in project_deps:
            match = re.split(r'[=<>~]+', dep_str)
            if match:
                name = match[0].strip()
                version = dep_str[len(name):].strip() if len(match) > 1 else None
                if name:
                    deps.append(Dependency(
                        name=name,
                        version=version if version else None,
                        ecosystem="pypi",
                        category=_get_category("pypi", name),
                        evidence_path=rel_path
                    ))
                    
        # Check poetry dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for name, version in poetry_deps.items():
            if name == "python":
                continue
            v_str = str(version) if isinstance(version, (str, int, float)) else None
            deps.append(Dependency(
                name=name,
                version=v_str,
                ecosystem="pypi",
                category=_get_category("pypi", name),
                evidence_path=rel_path
            ))
    except Exception as e:
        logger.warning(f"Failed to parse pyproject.toml at {rel_path}: {e}")
    return deps


def parse_pom_xml(content: str, rel_path: str) -> List[Dependency]:
    deps = []
    try:
        # Strip xmlns to make searching simpler, or just use regex fallback if XML fails
        content = re.sub(r'\sxmlns="[^"]+"', '', content, count=1)
        root = ET.fromstring(content)
        
        # Maven <dependencies> can be under project directly or dependencyManagement
        for dep in root.findall(".//dependency"):
            group_id = dep.findtext("groupId")
            artifact_id = dep.findtext("artifactId")
            version = dep.findtext("version")
            
            if group_id and artifact_id:
                name = f"{group_id}:{artifact_id}"
                deps.append(Dependency(
                    name=name,
                    version=version,
                    ecosystem="maven",
                    category=_get_category("maven", name),
                    evidence_path=rel_path
                ))
    except Exception as e:
        logger.warning(f"Failed to parse pom.xml at {rel_path}: {e}")
    return deps


def parse_docker_compose(content: str, rel_path: str) -> List[Dependency]:
    deps = []
    if not yaml:
        logger.warning("PyYAML not installed, skipping docker-compose.yml parsing.")
        return deps
        
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return deps
            
        services = data.get("services", {})
        if not isinstance(services, dict):
            return deps
            
        for svc_name, svc_conf in services.items():
            if isinstance(svc_conf, dict) and "image" in svc_conf:
                image = svc_conf["image"]
                
                # Split image name and tag/digest
                parts = image.split(":")
                name = parts[0]
                version = parts[1] if len(parts) > 1 else "latest"
                
                deps.append(Dependency(
                    name=name,
                    version=version,
                    ecosystem="docker",
                    category=_get_category("docker", name),
                    evidence_path=rel_path
                ))
    except Exception as e:
        logger.warning(f"Failed to parse docker-compose.yml at {rel_path}: {e}")
    return deps


def analyze_dependencies(base_path: str, manifest_paths: List[str]) -> RepositoryDependencies:
    """
    Parses manifest files discovered by Stage 1 to extract declared dependencies.
    """
    repo_deps = RepositoryDependencies()
    base = Path(base_path)
    
    for rel_path in manifest_paths:
        file_path = base / rel_path
        if not file_path.exists() or not file_path.is_file():
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="utf-16")
            except Exception as e:
                logger.warning(f"Could not read {rel_path} with utf-16: {e}")
                continue
        except Exception as e:
            logger.warning(f"Could not read {rel_path}: {e}")
            continue
            
        filename = file_path.name.lower()
        
        if filename == "package.json":
            repo_deps.dependencies.extend(parse_package_json(content, rel_path))
        elif filename == "requirements.txt":
            repo_deps.dependencies.extend(parse_requirements_txt(content, rel_path))
        elif filename == "pyproject.toml":
            repo_deps.dependencies.extend(parse_pyproject_toml(content, rel_path))
        elif filename == "pom.xml":
            repo_deps.dependencies.extend(parse_pom_xml(content, rel_path))
        elif filename in ("docker-compose.yml", "docker-compose.yaml"):
            repo_deps.dependencies.extend(parse_docker_compose(content, rel_path))
            
    return repo_deps
