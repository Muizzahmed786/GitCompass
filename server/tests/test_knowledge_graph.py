import unittest
from unittest.mock import MagicMock
from app.services.knowledge_graph import build_knowledge_graph

class TestKnowledgeGraph(unittest.IsolatedAsyncioTestCase):

    async def test_build_knowledge_graph_empty(self):
        """Empty repository yields empty graph."""
        db_mock = MagicMock()
        
        # Mock dependencies table
        dep_execute = MagicMock(return_value=MagicMock(data=[]))
        dep_eq = MagicMock(return_value=MagicMock(execute=dep_execute))
        dep_select = MagicMock(return_value=MagicMock(eq=dep_eq))
        
        # Mock source_files table
        file_execute = MagicMock(return_value=MagicMock(data=[]))
        file_eq = MagicMock(return_value=MagicMock(execute=file_execute))
        file_select = MagicMock(return_value=MagicMock(eq=file_eq))
        
        def side_effect(table_name):
            if table_name == "repository_dependencies":
                return MagicMock(select=dep_select)
            elif table_name == "repository_source_files":
                return MagicMock(select=file_select)
                
        db_mock.table.side_effect = side_effect
        
        res = await build_knowledge_graph(db_mock, "repo-123")
        self.assertEqual(len(res.nodes), 0)
        self.assertEqual(len(res.edges), 0)

    async def test_build_knowledge_graph_duplicate_and_self_deps(self):
        """Verify handling of duplicate, self, and circular dependencies."""
        db_mock = MagicMock()
        
        # Dependencies mock
        dep_execute = MagicMock(return_value=MagicMock(data=[
            {"name": "react", "category": "framework", "evidence_path": "package.json"}
        ]))
        dep_eq = MagicMock(return_value=MagicMock(execute=dep_execute))
        dep_select = MagicMock(return_value=MagicMock(eq=dep_eq))
        
        # Source files mock
        file_execute = MagicMock(return_value=MagicMock(data=[
            {
                "file_path": "src/A.js",
                "imports": ["react", "src/B", "src/A"]
            },
            {
                "file_path": "src/B.js",
                "imports": ["react", "src/A"]
            }
        ]))
        file_eq = MagicMock(return_value=MagicMock(execute=file_execute))
        file_select = MagicMock(return_value=MagicMock(eq=file_eq))
        
        def side_effect(table_name):
            if table_name == "repository_dependencies":
                return MagicMock(select=dep_select)
            elif table_name == "repository_source_files":
                return MagicMock(select=file_select)
                
        db_mock.table.side_effect = side_effect
        
        res = await build_knowledge_graph(db_mock, "repo-123")
        
        node_ids = {n.id for n in res.nodes}
        self.assertIn("dep_react", node_ids)
        self.assertIn("mod_root", node_ids)
        self.assertIn("mod_src", node_ids)
        
        edge_tuples = {(e.source, e.target, e.type) for e in res.edges}
        
        self.assertIn(("mod_root", "dep_react", "declares"), edge_tuples)
        self.assertIn(("mod_src", "dep_react", "imports"), edge_tuples)
        
        # Verify no self dependencies exist
        for e in res.edges:
            self.assertNotEqual(e.source, e.target, f"Self dependency found: {e.source} -> {e.target}")

    async def test_build_knowledge_graph_disconnected_and_limits(self):
        """Verify handling of disconnected modules and explicit truncation limits."""
        db_mock = MagicMock()
        
        # Dependencies mock - 600 dependencies
        dep_execute = MagicMock(return_value=MagicMock(data=[
            {"name": f"lib-{i}", "category": "framework", "evidence_path": None} for i in range(600)
        ]))
        dep_eq = MagicMock(return_value=MagicMock(execute=dep_execute))
        dep_select = MagicMock(return_value=MagicMock(eq=dep_eq))
        
        # Source files mock - 300 disconnected files (no imports)
        file_execute = MagicMock(return_value=MagicMock(data=[
            {
                "file_path": f"module_{i}/main.js",
                "imports": []
            } for i in range(300)
        ]))
        file_eq = MagicMock(return_value=MagicMock(execute=file_execute))
        file_select = MagicMock(return_value=MagicMock(eq=file_eq))
        
        def side_effect(table_name):
            if table_name == "repository_dependencies":
                return MagicMock(select=dep_select)
            elif table_name == "repository_source_files":
                return MagicMock(select=file_select)
                
        db_mock.table.side_effect = side_effect
        
        res = await build_knowledge_graph(db_mock, "repo-123")
        
        # Graph should be truncated at 200 nodes
        self.assertEqual(len(res.nodes), 200)
        self.assertTrue(res.is_truncated)
        
        # Edges should be 0 because nothing imports anything
        self.assertEqual(len(res.edges), 0)
