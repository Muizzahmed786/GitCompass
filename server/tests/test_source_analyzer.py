import unittest
import tempfile
from pathlib import Path

from app.services.source_analyzer import analyze_source_code

class TestSourceAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.test_dir.name)
        
    def tearDown(self):
        self.test_dir.cleanup()

    def _create_file(self, rel_path: str, content: str = ""):
        path = self.base_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        return path

    def test_python_parsing(self):
        content = """
import os
from typing import List as L, Optional
from fastapi import APIRouter

router = APIRouter()

@router.get('/api/users')
async def get_users(db: Session, limit: int = 10):
    pass

class BaseService:
    pass

class UserService(BaseService):
    @classmethod
    def get_all(cls):
        pass
"""
        self._create_file("backend/app/main.py", content)
        
        repo_ast = analyze_source_code(str(self.base_path), ["backend/app/main.py"])
        self.assertEqual(len(repo_ast.files), 1)
        file_ast = repo_ast.files[0]
        
        self.assertEqual(file_ast.language, "python")
        
        # Imports
        self.assertEqual(len(file_ast.imports), 3)
        typing_import = next(i for i in file_ast.imports if i.source == "typing")
        self.assertIn("List", typing_import.names)
        self.assertIn("L", typing_import.aliases)
        
        # Functions
        self.assertEqual(len(file_ast.functions), 1)
        get_users = file_ast.functions[0]
        self.assertEqual(get_users.name, "get_users")
        self.assertTrue(get_users.is_async)
        self.assertEqual(get_users.parameters, ["db", "limit"])
        self.assertIn("@router.get('/api/users')", get_users.decorators)
        
        # Classes
        self.assertEqual(len(file_ast.classes), 2)
        user_service = next(c for c in file_ast.classes if c.name == "UserService")
        self.assertIn("BaseService", user_service.base_classes)
        self.assertEqual(len(user_service.methods), 1)
        
        method = user_service.methods[0]
        self.assertEqual(method.name, "get_all")
        self.assertIn("@classmethod", method.decorators)
        self.assertEqual(method.parameters, ["cls"])

    def test_javascript_typescript_parsing(self):
        content = """
import React, { useState as useS, useEffect } from 'react';

export class App extends React.Component {
    @observable
    render() {
        return <div />;
    }
}

async function fetchData(url, options = {}) {
    console.log(url);
}
"""
        self._create_file("frontend/src/App.tsx", content)
        
        repo_ast = analyze_source_code(str(self.base_path), ["frontend/src/App.tsx"])
        if not repo_ast.files:
            self.skipTest("TSX parser not available")
            return
            
        file_ast = repo_ast.files[0]
        self.assertEqual(file_ast.language, "tsx")
        
        # Imports
        self.assertEqual(len(file_ast.imports), 1)
        react_import = file_ast.imports[0]
        self.assertEqual(react_import.source, "react")
        self.assertIn("useState", react_import.names)
        self.assertIn("useS", react_import.aliases)
        
        # Classes
        self.assertEqual(len(file_ast.classes), 1)
        app_class = file_ast.classes[0]
        self.assertEqual(app_class.name, "App")
        self.assertEqual(app_class.base_classes, ["React.Component"])
        self.assertEqual(len(app_class.methods), 1)
        self.assertEqual(app_class.methods[0].name, "render")
        self.assertIn("@observable", app_class.methods[0].decorators)
        
        # Functions
        self.assertEqual(len(file_ast.functions), 1)
        fetch = file_ast.functions[0]
        self.assertEqual(fetch.name, "fetchData")
        self.assertTrue(fetch.is_async)
        self.assertEqual(fetch.parameters, ["url", "options"])

    def test_malformed_syntax_recovery(self):
        content = """
def good_function():
    pass

def bad_function():
    syntax error this makes no sense!

class GoodClass:
    def good_method(self):
        pass
"""
        self._create_file("test.py", content)
        repo_ast = analyze_source_code(str(self.base_path), ["test.py"])
        file_ast = repo_ast.files[0]
        
        # Should still recover the good structures
        func_names = [f.name for f in file_ast.functions]
        self.assertIn("good_function", func_names)
        
        class_names = [c.name for c in file_ast.classes]
        self.assertIn("GoodClass", class_names)
        self.assertEqual(file_ast.classes[0].methods[0].name, "good_method")

    def test_unsupported_extensions(self):
        self._create_file("test.java", "class A {}")
        repo_ast = analyze_source_code(str(self.base_path), ["test.java"])
        self.assertEqual(len(repo_ast.files), 0)

if __name__ == "__main__":
    unittest.main()
