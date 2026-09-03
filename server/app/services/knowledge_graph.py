import logging
import json
from typing import Any, Dict, List, Set

from app.schemas.analytics import KnowledgeGraphResponse, GraphNode, GraphEdge

logger = logging.getLogger("gitcompass.knowledge_graph")


async def build_knowledge_graph(db: Any, repo_id: str) -> KnowledgeGraphResponse:
    """
    Constructs a deterministic, UI-agnostic knowledge graph for the repository.
    Strictly aggregates data from the existing Repository Knowledge Model.
    
    Implements Large-Graph Handling:
    - Defaults to Module/Service level grouping (by top-level directory)
    - Limits edges to prevent massive hairballs.
    """
    nodes = []
    edges = []
    nodes_map: Set[str] = set()

    # 1. Gather Dependencies (External Services/Modules)
    deps_res = db.table("repository_dependencies").select("*").eq("repo_id", repo_id).execute()
    
    if deps_res.data:
        for dep in deps_res.data:
            node_id = f"dep_{dep['name']}"
            if node_id not in nodes_map:
                nodes.append(GraphNode(
                    id=node_id,
                    label=dep["name"],
                    type="dependency",
                    category=dep.get("category") or "library"
                ))
                nodes_map.add(node_id)
                
            # Evidence path (where it was declared)
            if dep.get("evidence_path"):
                evidence_module = dep["evidence_path"].split('/')[0] if '/' in dep["evidence_path"] else "root"
                mod_id = f"mod_{evidence_module}"
                if mod_id not in nodes_map:
                    nodes.append(GraphNode(
                        id=mod_id,
                        label=evidence_module,
                        type="module",
                        category="source"
                    ))
                    nodes_map.add(mod_id)
                    
                edge_id = f"edge_{mod_id}_{node_id}"
                edges.append(GraphEdge(
                    id=edge_id,
                    source=mod_id,
                    target=node_id,
                    type="declares"
                ))

    # 2. Gather Source Files (Grouped into Modules)
    # We group by top-level directory to prevent massive graphs (Requirement #3)
    files_res = db.table("repository_source_files").select("*").eq("repo_id", repo_id).execute()
    
    if files_res.data:
        for f in files_res.data:
            path_parts = f["file_path"].split('/')
            # E.g. 'server/app/main.py' -> 'server'
            # If it's a root file 'main.py' -> 'root'
            module_name = path_parts[0] if len(path_parts) > 1 else "root"
            mod_id = f"mod_{module_name}"
            
            if mod_id not in nodes_map:
                nodes.append(GraphNode(
                    id=mod_id,
                    label=module_name,
                    type="module",
                    category="source"
                ))
                nodes_map.add(mod_id)

            # Map inter-module imports
            imports = f.get("imports", [])
            for imp in imports:
                if isinstance(imp, dict):
                    imp_name = imp.get("module") or imp.get("name")
                else:
                    imp_name = imp
                    
                if not imp_name:
                    continue
                    
                # Simplistic module matching for internal imports
                imp_module = imp_name.split('.')[0].split('/')[0]
                
                # Check if it matches a known dependency
                dep_id = f"dep_{imp_module}"
                if dep_id in nodes_map:
                    edges.append(GraphEdge(
                        id=f"edge_{mod_id}_{dep_id}",
                        source=mod_id,
                        target=dep_id,
                        type="imports"
                    ))
                else:
                    # Treat as internal module import if not self
                    target_mod_id = f"mod_{imp_module}"
                    if target_mod_id != mod_id:
                        # We lazily add the target module node if it doesn't exist
                        if target_mod_id not in nodes_map:
                            nodes.append(GraphNode(
                                id=target_mod_id,
                                label=imp_module,
                                type="module",
                                category="source"
                            ))
                            nodes_map.add(target_mod_id)
                            
                        edges.append(GraphEdge(
                            id=f"edge_{mod_id}_{target_mod_id}",
                            source=mod_id,
                            target=target_mod_id,
                            type="imports"
                        ))

    # Deduplicate edges (Requirement #5: Handle duplicate dependencies)
    unique_edges = {}
    for edge in edges:
        if edge.source == edge.target:
            continue # Self-dependencies filtered out
        if edge.id not in unique_edges:
            unique_edges[edge.id] = edge

    final_edges = list(unique_edges.values())
    
    # Cap limits for safety
    is_truncated = False
    if len(nodes) > 200:
        nodes = nodes[:200]
        is_truncated = True
    if len(final_edges) > 500:
        final_edges = final_edges[:500]
        is_truncated = True

    return KnowledgeGraphResponse(nodes=nodes, edges=final_edges, is_truncated=is_truncated)
