import unittest
import tempfile
import json
import os
from pathlib import Path

from app.services.structure_analyzer import analyze_repository_structure

class TestStructureAnalyzer(unittest.TestCase):
    
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

    def test_java_spring_detection(self):
        self._create_file("pom.xml", "<project><dependencies><dependency><artifactId>spring-boot-starter</artifactId></dependency></dependencies></project>")
        self._create_file("src/main/java/com/example/App.java", "class App {}")
        self._create_file("src/test/java/com/example/AppTest.java", "class AppTest {}")
        self._create_file("README.md", "# Spring App")
        
        struct = analyze_repository_structure(str(self.base_path))
        
        self.assertEqual(struct.languages.get("Java"), 2)
        self.assertIn("Maven", struct.buildTools)
        
        # Framework
        self.assertTrue(any(f.name == "Spring Boot" for f in struct.frameworks))
        
        # Directories
        self.assertIn("src", struct.directories.source)
        self.assertIn("src/test", struct.directories.tests)
        
        # Metadata
        self.assertIn("README.md", struct.metadataFiles)
        
        # Stats
        self.assertEqual(struct.statistics.codeFiles, 2)
        self.assertEqual(struct.statistics.testFiles, 1)

    def test_javascript_node_detection(self):
        package_json = {
            "dependencies": {
                "react": "18.0.0"
            }
        }
        self._create_file("package.json", json.dumps(package_json))
        self._create_file("client/src/index.js", "console.log('hi');")
        self._create_file("__tests__/app.test.js", "test('ok', () => {});")
        
        struct = analyze_repository_structure(str(self.base_path))
        
        self.assertEqual(struct.languages.get("JavaScript"), 2)
        self.assertIn("npm", struct.packageManagers)
        
        # Framework
        self.assertTrue(any(f.name == "React" for f in struct.frameworks))
        
        # Directories
        self.assertIn("client", struct.directories.source)
        self.assertIn("__tests__", struct.directories.tests)
        
        # Stats
        self.assertEqual(struct.statistics.codeFiles, 2)
        self.assertEqual(struct.statistics.testFiles, 1)

    def test_python_fastapi_detection(self):
        self._create_file("pyproject.toml", "dependencies = ['fastapi']")
        self._create_file("src/main.py", "print('hello')")
        self._create_file("tests/test_main.py", "def test_ok(): pass")
        self._create_file(".env.example", "KEY=VAL")
        
        struct = analyze_repository_structure(str(self.base_path))
        
        self.assertEqual(struct.languages.get("Python"), 2)
        self.assertIn("pip/poetry", struct.packageManagers)
        
        # Framework
        self.assertTrue(any(f.name == "FastAPI" for f in struct.frameworks))
        
        # Config
        self.assertIn(".env.example", struct.configurationFiles)

    def test_monorepo_detection(self):
        # Frontend
        self._create_file("frontend/package.json", json.dumps({"dependencies": {"next": "latest"}}))
        self._create_file("frontend/src/App.tsx", "")
        # Backend
        self._create_file("backend/requirements.txt", "django==4.0")
        self._create_file("backend/app/main.py", "")
        # Infra
        self._create_file(".github/workflows/deploy.yml", "")
        
        struct = analyze_repository_structure(str(self.base_path))
        
        self.assertEqual(struct.languages.get("TypeScript"), 1)
        self.assertEqual(struct.languages.get("Python"), 1)
        
        self.assertTrue(any(f.name == "Next.js" for f in struct.frameworks))
        self.assertTrue(any(f.name == "Django" for f in struct.frameworks))
        
        self.assertIn("frontend/src", struct.directories.source)
        self.assertIn("backend/app", struct.directories.source)
        
        self.assertTrue(any(c.platform == "GitHub Actions" for c in struct.ciCd))

    def test_ignore_rules(self):
        # Should be ignored
        self._create_file("node_modules/react/index.js", "")
        self._create_file(".git/config", "")
        self._create_file("target/classes/App.class", "")
        self._create_file("__pycache__/main.pyc", "")
        self._create_file(".venv/bin/python", "")
        
        # Valid files
        self._create_file("src/main.py", "")
        
        struct = analyze_repository_structure(str(self.base_path))
        
        self.assertEqual(struct.statistics.totalFiles, 1)
        self.assertEqual(struct.languages.get("Python"), 1)
        self.assertNotIn("JavaScript", struct.languages)

    def test_edge_cases(self):
        # Empty
        struct = analyze_repository_structure(str(self.base_path))
        self.assertEqual(struct.statistics.totalFiles, 0)
        
        # Docs only
        self._create_file("docs/index.md", "")
        self._create_file("README", "")
        struct = analyze_repository_structure(str(self.base_path))
        self.assertEqual(struct.statistics.totalFiles, 2)
        self.assertEqual(struct.statistics.codeFiles, 0)
        self.assertIn("docs", struct.directories.documentation)

if __name__ == "__main__":
    unittest.main()
