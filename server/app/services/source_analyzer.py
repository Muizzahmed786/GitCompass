import logging
from pathlib import Path
from typing import List, Optional, Tuple
import tree_sitter

from app.schemas.source_code import (
    RepositorySourceCode, FileAST, ImportDef, ClassDef, FunctionDef
)

logger = logging.getLogger("gitcompass.source_analyzer")

LANGUAGES = {}

try:
    import tree_sitter_python
    LANGUAGES["python"] = tree_sitter.Language(tree_sitter_python.language())
except ImportError:
    logger.warning("tree_sitter_python not installed")

try:
    import tree_sitter_javascript
    LANGUAGES["javascript"] = tree_sitter.Language(tree_sitter_javascript.language())
except ImportError:
    logger.warning("tree_sitter_javascript not installed")

try:
    import tree_sitter_typescript
    LANGUAGES["typescript"] = tree_sitter.Language(tree_sitter_typescript.language_typescript())
    LANGUAGES["tsx"] = tree_sitter.Language(tree_sitter_typescript.language_tsx())
except ImportError:
    logger.warning("tree_sitter_typescript not installed")


EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript", # Reusing JS grammar which usually supports JSX if configured, or we just map it. Actually, JS grammar supports JSX.
    ".ts": "typescript",
    ".tsx": "tsx"
}


def _extract_text(node, source_bytes: bytes) -> str:
    if node is None:
        return ""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')


def _get_decorators_python(node, source_bytes: bytes) -> List[str]:
    decorators = []
    # In python, decorators are siblings to the function/class def in some versions, or children.
    # Usually they are named children of the function_definition called 'decorator'
    for child in node.children:
        if child.type == "decorator":
            decorators.append(_extract_text(child, source_bytes))
    return decorators


def _get_decorators_js(node, source_bytes: bytes) -> List[str]:
    decorators = []
    for child in node.children:
        if child.type == "decorator":
            decorators.append(_extract_text(child, source_bytes))
    return decorators


def _get_parameters_python(node, source_bytes: bytes) -> List[str]:
    params = []
    params_node = node.child_by_field_name("parameters")
    if params_node:
        for p in params_node.children:
            if p.type in ("identifier", "typed_parameter", "default_parameter", "dictionary_splat_pattern", "list_splat_pattern", "typed_default_parameter"):
                # Just extract the name part
                if p.type == "identifier":
                    params.append(_extract_text(p, source_bytes))
                elif p.type in ("typed_parameter", "default_parameter", "typed_default_parameter"):
                    id_node = p.child_by_field_name("name") or p.child(0)
                    if id_node:
                        params.append(_extract_text(id_node, source_bytes))
                else:
                    params.append(_extract_text(p, source_bytes))
    return params


def _get_parameters_js(node, source_bytes: bytes) -> List[str]:
    params = []
    params_node = node.child_by_field_name("parameters")
    if params_node:
        for p in params_node.children:
            if p.type in ("identifier", "required_parameter", "optional_parameter", "assignment_pattern"):
                if p.type == "identifier":
                    params.append(_extract_text(p, source_bytes))
                elif p.type in ("required_parameter", "optional_parameter", "assignment_pattern"):
                    id_node = p.child_by_field_name("pattern") or p.child(0)
                    if id_node:
                        params.append(_extract_text(id_node, source_bytes))
                else:
                    params.append(_extract_text(p, source_bytes))
    return params


def parse_python_file(root_node, source_bytes: bytes, file_path: str) -> FileAST:
    imports = []
    classes = []
    functions = []
    
    # Simple recursive descent
    def visit(node, inside_class=None, pending_decorators=None):
        if node.type == "import_statement":
            names = []
            aliases = []
            for child in node.children:
                if child.type == "dotted_name":
                    names.append(_extract_text(child, source_bytes))
                    aliases.append("")
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    alias_node = child.child_by_field_name("alias")
                    names.append(_extract_text(name_node, source_bytes) if name_node else "")
                    aliases.append(_extract_text(alias_node, source_bytes) if alias_node else "")
            
            if names:
                imports.append(ImportDef(source="<builtin/global>", names=names, aliases=aliases))
                
        elif node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            source_mod = _extract_text(module_node, source_bytes) if module_node else ""
            
            names = []
            aliases = []
            for child in node.children:
                if child.type == "dotted_name" and child != module_node:
                    names.append(_extract_text(child, source_bytes))
                    aliases.append("")
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    alias_node = child.child_by_field_name("alias")
                    names.append(_extract_text(name_node, source_bytes) if name_node else "")
                    aliases.append(_extract_text(alias_node, source_bytes) if alias_node else "")
            
            if names:
                imports.append(ImportDef(source=source_mod, names=names, aliases=aliases))
                
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = _extract_text(name_node, source_bytes) if name_node else "<anonymous>"
            
            base_classes = []
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                for sc in superclasses.children:
                    if sc.type in ("identifier", "attribute"):
                        base_classes.append(_extract_text(sc, source_bytes))
            
            cdef = ClassDef(
                name=class_name,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                base_classes=base_classes,
                methods=[]
            )
            classes.append(cdef)
            
            # Visit children but inside this class
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    visit(child, inside_class=cdef)
            return # Don't visit children again
            
        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            func_name = _extract_text(name_node, source_bytes) if name_node else "<anonymous>"
            
            is_async = "async" in _extract_text(node, source_bytes).split(" ")[0]
            
            fdef = FunctionDef(
                name=func_name,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                is_async=is_async,
                parameters=_get_parameters_python(node, source_bytes),
                decorators=pending_decorators or []
            )
            
            if inside_class is not None:
                inside_class.methods.append(fdef)
            else:
                functions.append(fdef)
                
            return

        elif node.type == "decorated_definition":
            decorators = []
            for child in node.children:
                if child.type == "decorator":
                    decorators.append(_extract_text(child, source_bytes))
            
            definition = node.child_by_field_name("definition")
            if not definition:
                for child in node.children:
                    if child.type in ("function_definition", "class_definition"):
                        definition = child
                        break
            
            if definition:
                visit(definition, inside_class, pending_decorators=decorators)
            return

        for child in node.children:
            visit(child, inside_class, pending_decorators)

    visit(root_node)
    
    return FileAST(
        file_path=file_path,
        language="python",
        imports=imports,
        classes=classes,
        functions=functions
    )


def parse_js_ts_file(root_node, source_bytes: bytes, file_path: str, language: str) -> FileAST:
    imports = []
    classes = []
    functions = []

    def visit(node, inside_class=None, pending_decorators=None):
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            source_mod = _extract_text(source_node, source_bytes).strip("\"'") if source_node else ""
            
            names = []
            aliases = []
            
            # js imports can have import_clause
            clause = node.child_by_field_name("import") # Note: tree-sitter JS calls it import_clause, but let's just search children
            for child in node.children:
                if child.type == "import_clause":
                    for c in child.children:
                        if c.type == "identifier":
                            names.append(_extract_text(c, source_bytes))
                            aliases.append("")
                        elif c.type == "named_imports":
                            for ni in c.children:
                                if ni.type == "import_specifier":
                                    n = ni.child_by_field_name("name")
                                    a = ni.child_by_field_name("alias")
                                    names.append(_extract_text(n, source_bytes) if n else "")
                                    aliases.append(_extract_text(a, source_bytes) if a else "")
            
            if names:
                imports.append(ImportDef(source=source_mod, names=names, aliases=aliases))
                
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = _extract_text(name_node, source_bytes) if name_node else "<anonymous>"
            
            base_classes = []
            hc = None
            for child in node.children:
                if child.type == "class_heritage":
                    hc = child
                    break
                    
            if hc:
                # heritage clause contains extends_clause or implements_clause
                for child in hc.children:
                    if child.type == "extends_clause" or child.type == "implements_clause":
                        for c in child.children:
                            if c.type in ("identifier", "member_expression"):
                                base_classes.append(_extract_text(c, source_bytes))
                    elif child.type in ("identifier", "member_expression"):
                        base_classes.append(_extract_text(child, source_bytes))
            # Some versions just have 'class_heritage' with a member expression inside
            for child in node.children:
                if child.type == "class_heritage":
                    for c in child.children:
                        if c.type in ("identifier", "member_expression"):
                            base_classes.append(_extract_text(c, source_bytes))
            
            cdef = ClassDef(
                name=class_name,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                base_classes=base_classes,
                methods=[]
            )
            classes.append(cdef)
            
            body = node.child_by_field_name("body")
            if body:
                visit(body, inside_class=cdef)
            return
            
        elif node.type in ("function_declaration", "method_definition", "arrow_function"):
            name_node = node.child_by_field_name("name")
            func_name = _extract_text(name_node, source_bytes) if name_node else "<anonymous>"
            
            # Arrow functions often don't have a direct name node unless assigned. We'll skip deep assignment tracking for MVP.
            
            is_async = False
            for child in node.children:
                if child.type == "async":
                    is_async = True
                    break
                    
            fdef = FunctionDef(
                name=func_name,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                is_async=is_async,
                parameters=_get_parameters_js(node, source_bytes),
                decorators=pending_decorators or _get_decorators_js(node, source_bytes)
            )
            
            if node.type == "method_definition" and inside_class is not None:
                inside_class.methods.append(fdef)
            elif node.type == "function_declaration":
                functions.append(fdef)
            
            # Don't recurse into function bodies
            return
            
        elif node.type == "class_body":
            pending = []
            for child in node.children:
                if child.type == "decorator":
                    pending.append(_extract_text(child, source_bytes))
                elif child.type in ("method_definition", "public_field_definition", "function_declaration"):
                    visit(child, inside_class, pending)
                    pending = []
                else:
                    visit(child, inside_class)
            return

        for child in node.children:
            visit(child, inside_class, pending_decorators)

    visit(root_node)

    return FileAST(
        file_path=file_path,
        language=language,
        imports=imports,
        classes=classes,
        functions=functions
    )


def analyze_source_code(base_path: str, source_files: List[str]) -> RepositorySourceCode:
    """
    Parses source files discovered by Stage 1 to extract structural AST metadata.
    """
    repo_ast = RepositorySourceCode()
    base = Path(base_path)
    
    for rel_path in source_files:
        file_path = base / rel_path
        ext = file_path.suffix.lower()
        
        if ext not in EXTENSION_MAP:
            continue
            
        lang_key = EXTENSION_MAP[ext]
        if lang_key not in LANGUAGES:
            continue
            
        try:
            source_bytes = file_path.read_bytes()
            parser = tree_sitter.Parser()
            parser.language = LANGUAGES[lang_key]
            
            tree = parser.parse(source_bytes)
            
            if tree.root_node.has_error:
                logger.warning(f"Syntax errors detected in {rel_path} - extracting recoverable structures")
                
            if lang_key == "python":
                file_ast = parse_python_file(tree.root_node, source_bytes, rel_path)
            else:
                file_ast = parse_js_ts_file(tree.root_node, source_bytes, rel_path, lang_key)
                
            repo_ast.files.append(file_ast)
            
        except Exception as e:
            logger.warning(f"Failed to process source file {rel_path}: {e}")
            
    return repo_ast
