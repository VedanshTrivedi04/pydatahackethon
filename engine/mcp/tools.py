import uuid
import logging
import asyncio
from typing import Optional, List, Dict, Any

# Import module run handlers
from engine.modules.scaffolder import handler as scaffolder
from engine.modules.test_generator import handler as test_generator
from engine.modules.docs_generator import handler as docs_generator
from engine.modules.changelog_generator import handler as changelog_generator
from engine.modules.notebook_to_blog import handler as notebook_to_blog

logger = logging.getLogger("engine.mcp.tools")

def get_job_and_tenant() -> tuple[str, str]:
    return str(uuid.uuid4()), "default-mcp-tenant"

async def scaffold_project_tool(
    project_name: str,
    stack: str = "fastapi",
    description: Optional[str] = None
) -> str:
    """
    Scaffolds a new project skeleton.
    
    Args:
        project_name: The name of the project directory (e.g. 'my_api')
        stack: The technology stack to use. Currently supports 'fastapi'.
        description: An optional brief description of what the project does to customize the README.
    """
    job_id, tenant_id = get_job_and_tenant()
    payload = {
        "stack": stack,
        "project_name": project_name,
        "description": description or f"A clean {stack} project."
    }
    
    result = await scaffolder.run(job_id, tenant_id, payload)
    
    if result.status == "success":
        return f"Successfully scaffolded project '{project_name}' using stack '{stack}'.\n" \
               f"Artifact ZIP Key: {result.output.get('artifact_key')}\n\n" \
               f"README Preview:\n{result.output.get('readme_summary')}"
    else:
        return f"Failed to scaffold project: {result.error}"

async def generate_tests_tool(
    file_content: str,
    repo_context: str = "Python Module"
) -> str:
    """
    Analyzes Python source code and generates matching pytest tests.
    Runs the tests in an isolated sandbox subprocess and retries once if they fail.
    
    Args:
        file_content: The actual Python source code that needs test coverage.
        repo_context: Context about the module or package to guide the LLM.
    """
    job_id, tenant_id = get_job_and_tenant()
    payload = {
        "file_content": file_content,
        "repo_context": repo_context
    }
    
    result = await test_generator.run(job_id, tenant_id, payload)
    
    if result.status in ("success", "partial"):
        status_msg = "Passed" if result.output.get("sandbox_passed") else "Failed sandbox verification"
        ret = f"Test Generation Status: {result.status.upper()} ({status_msg})\n" \
              f"Artifact Test Key: {result.output.get('artifact_key')}\n\n" \
              f"Generated Pytest Code:\n```python\n{result.output.get('test_code')}\n```\n\n" \
              f"Sandbox Execution Output:\n{result.output.get('sandbox_output')}"
        return ret
    else:
        return f"Failed to generate tests: {result.error}"

async def generate_api_docs_tool(
    file_content: str,
    framework: str = "fastapi"
) -> str:
    """
    Extracts routes from a FastAPI, Flask, or Django web application file and
    generates an OpenAPI 3.0 YAML spec and formatted Markdown API docs.
    
    Args:
        file_content: The python source code containing the web framework routes.
        framework: The framework name, e.g. 'fastapi', 'flask', or 'django'.
    """
    job_id, tenant_id = get_job_and_tenant()
    payload = {
        "file_content": file_content,
        "framework": framework
    }
    
    result = await docs_generator.run(job_id, tenant_id, payload)
    
    if result.status == "success":
        ret = f"Successfully generated API documentation.\n" \
              f"OpenAPI YAML Key: {result.output.get('openapi_key')}\n" \
              f"Markdown Doc Key: {result.output.get('markdown_key')}\n\n" \
              f"Generated Markdown Docs:\n{result.output.get('api_docs_md')}\n\n" \
              f"Generated OpenAPI YAML:\n```yaml\n{result.output.get('openapi_yaml')}\n```"
        return ret
    else:
        return f"Failed to generate API docs: {result.error}"

async def generate_changelog_tool(
    commit_range: str = "HEAD~5..HEAD",
    repo_url: Optional[str] = None
) -> str:
    """
    Parses git commits using conventional prefixes (feat, fix, chore) and writes
    a professional release summary markdown with recommended version bump (SemVer).
    
    Args:
        commit_range: The git log range (e.g. 'v1.2.0..HEAD').
        repo_url: URL of the repository (e.g. 'https://github.com/org/repo').
    """
    job_id, tenant_id = get_job_and_tenant()
    payload = {
        "commit_range": commit_range,
        "repo_url": repo_url or "https://github.com/shipfaster/demo",
        "commits": []
    }
    
    result = await changelog_generator.run(job_id, tenant_id, payload)
    
    if result.status == "success":
        ret = f"Successfully generated release notes for version {result.output.get('version')}.\n" \
              f"Artifact Key: {result.output.get('changelog_key')}\n\n" \
              f"Release Notes:\n{result.output.get('release_notes_md')}"
        return ret
    else:
        return f"Failed to generate changelog: {result.error}"

async def notebook_to_blog_tool(
    notebook_content: str
) -> str:
    """
    Parses a Jupyter Notebook (.ipynb), extracts markdown, code snippets, and base64 plots,
    saves base64 images to static assets, and returns an engaging tech blog post draft.
    
    Args:
        notebook_content: Raw text content of the .ipynb JSON file.
    """
    job_id, tenant_id = get_job_and_tenant()
    payload = {
        "notebook_content": notebook_content
    }
    
    result = await notebook_to_blog.run(job_id, tenant_id, payload)
    
    if result.status == "success":
        ret = f"Successfully created blog post draft.\n" \
              f"Draft Key: {result.output.get('draft_key')}\n" \
              f"Extracted Image Keys: {result.output.get('image_keys')}\n\n" \
              f"Blog Draft Markdown:\n{result.output.get('blog_post_md')}"
        return ret
    else:
        return f"Failed to convert notebook to blog: {result.error}"
