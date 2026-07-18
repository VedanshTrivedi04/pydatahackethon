import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engine.mcp.server")

# Fallback for FastMCP library if not installed
try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    logger.warning("fastmcp not found. Implementing dummy FastMCP fallback class for local execution.")
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
            self.tools = {}
            
        def tool(self, name: str = None):
            def decorator(func):
                tool_name = name or func.__name__
                self.tools[tool_name] = func
                return func
            return decorator
            
        def run(self, **kwargs):
            logger.info(f"--- [Mock FastMCP Server '{self.name}'] Started (stdio transport) ---")
            logger.info("Registered Tools in mock mode:")
            for tool_name, func in self.tools.items():
                desc = func.__doc__.strip().split("\n")[0] if func.__doc__ else "No description"
                logger.info(f"  * {tool_name} -> {desc}")
            logger.info("Mock Server running. Exit by Ctrl+C.")
            import time
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Mock Server stopped.")
    HAS_FASTMCP = False

# 1. Initialize FastMCP Server (using real or mock fallback)
mcp = FastMCP("ShipFaster-Agent-Server")

# Import tools after FastMCP wrapper is defined
from engine.mcp import tools

# 2. Register tools
@mcp.tool(name="scaffold_project")
async def scaffold_project(
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
    logger.info(f"MCP Tool scaffold_project called for project: {project_name}")
    return await tools.scaffold_project_tool(project_name, stack, description)

@mcp.tool(name="generate_tests")
async def generate_tests(
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
    logger.info("MCP Tool generate_tests called.")
    return await tools.generate_tests_tool(file_content, repo_context)

@mcp.tool(name="generate_api_docs")
async def generate_api_docs(
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
    logger.info(f"MCP Tool generate_api_docs called for framework: {framework}")
    return await tools.generate_api_docs_tool(file_content, framework)

@mcp.tool(name="generate_changelog")
async def generate_changelog(
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
    logger.info(f"MCP Tool generate_changelog called for range: {commit_range}")
    return await tools.generate_changelog_tool(commit_range, repo_url)

@mcp.tool(name="notebook_to_blog")
async def notebook_to_blog(
    notebook_content: str
) -> str:
    """
    Parses a Jupyter Notebook (.ipynb), extracts markdown, code snippets, and base64 plots,
    saves base64 images to static assets, and returns an engaging tech blog post draft.
    
    Args:
        notebook_content: Raw text content of the .ipynb JSON file.
    """
    logger.info("MCP Tool notebook_to_blog called.")
    return await tools.notebook_to_blog_tool(notebook_content)

if __name__ == "__main__":
    logger.info("Starting ShipFaster FastMCP Server...")
    mcp.run()
