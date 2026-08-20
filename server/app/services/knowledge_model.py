import logging
from typing import Optional
from app.database import get_service_client
from app.schemas.structure import RepositoryStructure
from app.schemas.dependencies import RepositoryDependencies
from app.schemas.source_code import RepositorySourceCode

logger = logging.getLogger("gitcompass.knowledge_model")

def replace_knowledge_model(
    repo_id: str,
    latest_sha: str,
    structure: RepositoryStructure,
    dependencies: RepositoryDependencies,
    source_code: RepositorySourceCode
):
    """
    Replaces the repository knowledge model atomically via Supabase RPC.
    """
    logger.info("Replacing Knowledge Model for repo %s at sha %s", repo_id, latest_sha)
    db = get_service_client()
    
    # Serialize schemas to basic dictionaries
    struct_dict = structure.model_dump()
    
    deps_list = []
    for dep in dependencies.dependencies:
        deps_list.append({
            "name": dep.name,
            "version": dep.version,
            "ecosystem": dep.ecosystem,
            "category": dep.category,
            "evidence_path": dep.evidence_path
        })
            
    source_files_list = []
    for f in source_code.files:
        source_files_list.append({
            "file_path": f.file_path,
            "language": f.language,
            "imports": [i.model_dump() for i in f.imports],
            "classes": [c.model_dump() for c in f.classes],
            "functions": [fn.model_dump() for fn in f.functions]
        })
        
    try:
        # Call the RPC function defined in 008_knowledge_model.sql
        db.rpc(
            "replace_knowledge_model",
            {
                "p_repo_id": repo_id,
                "p_latest_sha": latest_sha,
                "p_structure": struct_dict,
                "p_dependencies": deps_list,
                "p_source_files": source_files_list
            }
        ).execute()
        logger.info("Successfully replaced Knowledge Model for repo %s", repo_id)
        
    except Exception as e:
        logger.error("Failed to replace Knowledge Model for repo %s: %s", repo_id, e)
        raise
