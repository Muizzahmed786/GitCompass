import unittest
import tempfile
import json
from pathlib import Path

from app.services.dependency_analyzer import analyze_dependencies

class TestDependencyAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.test_dir.name)
        
    def tearDown(self):
        self.test_dir.cleanup()

    def _create_file(self, rel_path: str, content: str = ""):
        path = self.base_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_package_json(self):
        content = json.dumps({
            "dependencies": {
                "react": "^18.0.0",
                "lodash": "4.17.21"
            },
            "devDependencies": {
                "jest": "29.0.0"
            }
        })
        self._create_file("package.json", content)
        
        repo_deps = analyze_dependencies(str(self.base_path), ["package.json"])
        deps = repo_deps.dependencies
        
        self.assertEqual(len(deps), 3)
        
        react = next(d for d in deps if d.name == "react")
        self.assertEqual(react.version, "^18.0.0")
        self.assertEqual(react.ecosystem, "npm")
        self.assertEqual(react.category, "framework")
        self.assertEqual(react.evidence_path, "package.json")
        
        lodash = next(d for d in deps if d.name == "lodash")
        self.assertEqual(lodash.category, "library")

    def test_requirements_txt(self):
        content = """
# A comment
django==4.2.0
requests>=2.0.0
pytest
        """
        self._create_file("backend/requirements.txt", content.strip())
        
        repo_deps = analyze_dependencies(str(self.base_path), ["backend/requirements.txt"])
        deps = repo_deps.dependencies
        
        self.assertEqual(len(deps), 3)
        django = next(d for d in deps if d.name == "django")
        self.assertEqual(django.version, "==4.2.0")
        self.assertEqual(django.category, "framework")
        self.assertEqual(django.evidence_path, "backend/requirements.txt")
        
        pytest = next(d for d in deps if d.name == "pytest")
        self.assertIsNone(pytest.version)

    def test_pyproject_toml(self):
        content = """
[project]
name = "test"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn"
]

[tool.poetry.dependencies]
pydantic = "^2.0.0"
        """
        self._create_file("pyproject.toml", content.strip())
        
        repo_deps = analyze_dependencies(str(self.base_path), ["pyproject.toml"])
        deps = repo_deps.dependencies
        
        # Depending on whether tomllib is present, it might be 0 or 3
        try:
            import tomllib
            self.assertEqual(len(deps), 3)
            fastapi = next(d for d in deps if d.name == "fastapi")
            self.assertEqual(fastapi.version, ">=0.100.0")
            self.assertEqual(fastapi.category, "framework")
        except ImportError:
            self.assertEqual(len(deps), 0)

    def test_pom_xml(self):
        content = """
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-web</artifactId>
                    <version>3.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.junit.jupiter</groupId>
                    <artifactId>junit-jupiter</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        self._create_file("services/api/pom.xml", content.strip())
        
        repo_deps = analyze_dependencies(str(self.base_path), ["services/api/pom.xml"])
        deps = repo_deps.dependencies
        
        self.assertEqual(len(deps), 2)
        spring = next(d for d in deps if "spring-boot" in d.name)
        self.assertEqual(spring.name, "org.springframework.boot:spring-boot-starter-web")
        self.assertEqual(spring.version, "3.0.0")
        self.assertEqual(spring.category, "framework")

    def test_docker_compose(self):
        content = """
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: supersecret
  web:
    image: nginx:alpine
  cache:
    image: redis
        """
        self._create_file("docker-compose.yml", content.strip())
        
        repo_deps = analyze_dependencies(str(self.base_path), ["docker-compose.yml"])
        deps = repo_deps.dependencies
        
        try:
            import yaml
            self.assertEqual(len(deps), 3)
            pg = next(d for d in deps if d.name == "postgres")
            self.assertEqual(pg.version, "15")
            self.assertEqual(pg.category, "database")
            
            # Ensure environment was NOT extracted
            for d in deps:
                self.assertNotIn("supersecret", str(d.model_dump()))
        except ImportError:
            pass

    def test_monorepo(self):
        self._create_file("frontend/package.json", '{"dependencies": {"react": "18"}}')
        self._create_file("backend/requirements.txt", "django")
        self._create_file("pom.xml", "<project><dependencies><dependency><groupId>g</groupId><artifactId>a</artifactId></dependency></dependencies></project>")
        
        manifests = ["frontend/package.json", "backend/requirements.txt", "pom.xml"]
        repo_deps = analyze_dependencies(str(self.base_path), manifests)
        
        self.assertEqual(len(repo_deps.dependencies), 3)
        ecosystems = {d.ecosystem for d in repo_deps.dependencies}
        self.assertEqual(ecosystems, {"npm", "pypi", "maven"})

    def test_malformed_json_graceful_handling(self):
        self._create_file("package.json", "{ bad json")
        # Should not crash
        repo_deps = analyze_dependencies(str(self.base_path), ["package.json"])
        self.assertEqual(len(repo_deps.dependencies), 0)

if __name__ == "__main__":
    unittest.main()
