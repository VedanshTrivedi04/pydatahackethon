import ast
import re
import logging
from typing import List, Dict, Any, Tuple
from engine.core.models import ModuleResult
from engine.core import storage
from engine.core import llm_client
from engine.prompts.docs_generator import DOCS_GENERATION_SYSTEM_PROMPT

logger = logging.getLogger("engine.modules.docs_generator")

def parse_routes_ast(code: str) -> List[Dict[str, Any]]:
    """
    Statically analyzes route files (FastAPI / Flask / Django) to find routes,
    request methods, function names, and docstrings.
    """
    routes = []
    try:
        tree = ast.parse(code)
    except Exception as e:
        logger.warning(f"Could not parse code in docs_generator: {str(e)}")
        return [{"error": f"Failed to parse source file: {str(e)}"}]
        
    class RouteVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # Check route decorators
            for decorator in node.decorator_list:
                dec_str = ""
                # Simple decorator name check (e.g. @app.get, @blueprint.route, @route)
                try:
                    if isinstance(decorator, ast.Call):
                        dec_str = ast.unparse(decorator.func)
                        args = [ast.unparse(arg) for arg in decorator.args]
                        keywords = {kw.arg: ast.unparse(kw.value) for kw in decorator.keywords if kw.arg}
                    else:
                        dec_str = ast.unparse(decorator)
                        args = []
                        keywords = {}
                except Exception:
                    dec_str = "decorator"
                    args = []
                    keywords = {}
                
                # Check for router / route patterns
                dec_lower = dec_str.lower()
                is_route = any(
                    pattern in dec_lower 
                    for pattern in ["route", "get", "post", "put", "delete", "patch", "options", "head"]
                )
                
                if is_route:
                    # Extract path from args or keywords if available
                    path = "'/'"
                    if args:
                        path = args[0]
                    elif "path" in keywords:
                        path = keywords["path"]
                    elif "rule" in keywords:
                        path = keywords["rule"]
                        
                    methods = keywords.get("methods", "['GET']")
                    
                    # Deduce methods from decorator name for FastAPI (e.g. app.get -> GET)
                    if "get" in dec_lower:
                        methods = "['GET']"
                    elif "post" in dec_lower:
                        methods = "['POST']"
                    elif "put" in dec_lower:
                        methods = "['PUT']"
                    elif "delete" in dec_lower:
                        methods = "['DELETE']"
                    elif "patch" in dec_lower:
                        methods = "['PATCH']"
                        
                    routes.append({
                        "decorator": dec_str,
                        "path": path.strip("'\""),
                        "methods": methods,
                        "function": node.name,
                        "docstring": ast.get_docstring(node) or "No description provided."
                    })
            self.generic_visit(node)
            
        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)
            
    visitor = RouteVisitor()
    visitor.visit(tree)
    
    # If no route decorators found, look for Django url patterns (regex/ast search for path or url)
    if not routes:
        django_paths = re.findall(r"(?:path|re_path)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*([\w\.]+)", code)
        for path_match, view_match in django_paths:
            routes.append({
                "decorator": "Django path",
                "path": path_match,
                "methods": "N/A (Django View)",
                "function": view_match,
                "docstring": "Django View Class / Function"
            })
            
    return routes

async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
    """
    Docs Generator module handler.
    Parses routes from source file, sends them to LLM, generates OpenAPI YAML and
    comprehensive Markdown documentation, and saves them.
    
    Payload shape:
    {
        "file_content": str,   # the python routes file code
        "framework": str       # e.g., "fastapi", "flask", "django"
    }
    """
    file_content = payload.get("file_content", "")
    framework = payload.get("framework", "fastapi").lower()
    
    if not file_content.strip():
        file_content = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/users")
def get_users():
    \"\"\"Retrieve users list.\"\"\"
    return [{"id": 1, "name": "Alice"}]

@app.post("/api/v1/users")
def create_user(user: dict):
    \"\"\"Create a new user.\"\"\"
    return {"status": "created"}
"""
        
    try:
        # 1. Parse route definitions
        logger.info("Analyzing API routes inside route file...")
        parsed_routes = parse_routes_ast(file_content)
        
        # 2. Request OpenAPI YAML generation
        logger.info("Requesting LLM to generate OpenAPI YAML spec...")
        openapi_prompt_user = f"""Based on the following {framework} route file, generate a valid and comprehensive OpenAPI 3.0 specification in YAML format.
Here is the source code:
```python
{file_content}
```

Parsed route information:
{parsed_routes}

Remember, output ONLY the raw YAML content, no markdown headers or fences.
"""
        openapi_yaml = await llm_client.complete(
            tenant_id=tenant_id,
            job_id=job_id,
            system=DOCS_GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": openapi_prompt_user}]
        )
        
        # Strip code fences from openapi YAML if LLM returned them
        openapi_yaml = openapi_yaml.strip()
        if openapi_yaml.startswith("```"):
            lines = openapi_yaml.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            openapi_yaml = "\n".join(lines).strip()
            
        # 3. Request Markdown documentation generation
        logger.info("Requesting LLM to generate Markdown documentation...")
        markdown_prompt_user = f"""Based on the following {framework} route file and the parsed route details, generate a beautiful, comprehensive API documentation in Markdown.
Here is the source code:
```python
{file_content}
```

Parsed route information:
{parsed_routes}

Provide clear headings, endpoint table, parameters description, authentication guide, and request/response examples.
Remember, output ONLY the raw Markdown content.
"""
        markdown_docs = await llm_client.complete(
            tenant_id=tenant_id,
            job_id=job_id,
            system=DOCS_GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": markdown_prompt_user}]
        )
        
        # Strip code fences from markdown if LLM returned them
        markdown_docs = markdown_docs.strip()
        if markdown_docs.startswith("```"):
            lines = markdown_docs.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            markdown_docs = "\n".join(lines).strip()

        # 4. Save artifacts
        yaml_key = storage.save_artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name="openapi.yaml",
            file_content=openapi_yaml.encode("utf-8"),
            content_type="application/yaml"
        )
        
        md_key = storage.save_artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name="api_docs.md",
            file_content=markdown_docs.encode("utf-8"),
            content_type="text/markdown"
        )
        
        return ModuleResult(
            status="success",
            output={
                "openapi_yaml": openapi_yaml,
                "api_docs_md": markdown_docs,
                "openapi_key": yaml_key,
                "markdown_key": md_key,
                "routes_parsed": parsed_routes
            },
            artifacts=[yaml_key, md_key],
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error in docs generator module execution: {str(e)}")
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error=str(e)
        )
