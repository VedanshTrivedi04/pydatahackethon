import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from engine.modules.scaffolder import handler as scaffolder
from engine.modules.test_generator import handler as test_generator
from engine.modules.docs_generator import handler as docs_generator
from engine.modules.changelog_generator import handler as changelog_generator
from engine.modules.notebook_to_blog import handler as notebook_to_blog

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("engine.tests.run_tests")

async def test_scaffolder():
    logger.info("--- Testing Scaffolder ---")
    payload = {
        "stack": "fastapi",
        "project_name": "SuperApp",
        "description": "An awesome enterprise web app."
    }
    res = await scaffolder.run("job-scaffold-1", "tenant-test", payload)
    logger.info(f"Result Status: {res.status}")
    logger.info(f"Output Keys: {list(res.output.keys())}")
    logger.info(f"Artifacts: {res.artifacts}")
    assert res.status == "success"
    logger.info("Scaffolder test passed!\n")

async def test_test_generator():
    logger.info("--- Testing Test Generator ---")
    file_content = """def calculate_discount(price, is_member):
    if price < 0:
        raise ValueError("Price cannot be negative")
    if is_member:
        return price * 0.9
    else:
        return price
"""
    payload = {
        "file_content": file_content,
        "repo_context": "Simple billing helper module"
    }
    res = await test_generator.run("job-test-gen-1", "tenant-test", payload)
    logger.info(f"Result Status: {res.status}")
    logger.info(f"Sandbox Passed: {res.output.get('sandbox_passed')}")
    logger.info(f"Generated Test Code Length: {len(res.output.get('test_code', ''))}")
    logger.info(f"Artifacts: {res.artifacts}")
    # Since sandbox runs in subprocess, it will run pytest.
    # It might pass or return partial depending on environment. It should not fail completely.
    assert res.status in ("success", "partial")
    logger.info("Test Generator test passed!\n")

async def test_docs_generator():
    logger.info("--- Testing Docs Generator ---")
    file_content = """from fastapi import FastAPI, Depends

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user_profile(user_id: int, include_details: bool = False):
    \"\"\"
    Retrieves user profile data by ID.
    \"\"\"
    return {"user_id": user_id, "active": True}

@app.post("/users")
async def create_user(data: dict):
    \"\"\"
    Creates a new user account.
    \"\"\"
    return {"id": 123, "status": "created"}
"""
    payload = {
        "file_content": file_content,
        "framework": "fastapi"
    }
    res = await docs_generator.run("job-docs-gen-1", "tenant-test", payload)
    logger.info(f"Result Status: {res.status}")
    logger.info(f"Markdown Docs Length: {len(res.output.get('api_docs_md', ''))}")
    logger.info(f"OpenAPI YAML Length: {len(res.output.get('openapi_yaml', ''))}")
    logger.info(f"Artifacts: {res.artifacts}")
    assert res.status == "success"
    logger.info("Docs Generator test passed!\n")

async def test_changelog_generator():
    logger.info("--- Testing Changelog Generator ---")
    payload = {
        "commit_range": "HEAD~5..HEAD",
        "repo_url": "https://github.com/shipfaster/engine",
        "commits": [
            {"hash": "11111111", "message": "feat(api): add healthcheck endpoint", "body": ""},
            {"hash": "22222222", "message": "fix(worker): resolve redis memory leak", "body": ""},
            {"hash": "33333333", "message": "feat(auth)!: enforce JWT sign verification", "body": "BREAKING CHANGE: Older bearer tokens are deprecated."}
        ]
    }
    res = await changelog_generator.run("job-changelog-1", "tenant-test", payload)
    logger.info(f"Result Status: {res.status}")
    logger.info(f"Release Notes Version: {res.output.get('version')}")
    logger.info(f"Release Notes Length: {len(res.output.get('release_notes_md', ''))}")
    logger.info(f"Artifacts: {res.artifacts}")
    assert res.status == "success"
    logger.info("Changelog Generator test passed!\n")

async def test_notebook_to_blog():
    logger.info("--- Testing Notebook to Blog ---")
    payload = {
        "notebook_content": "" # Triggers handler's dummy mock generator
    }
    res = await notebook_to_blog.run("job-notebook-1", "tenant-test", payload)
    logger.info(f"Result Status: {res.status}")
    logger.info(f"Blog post length: {len(res.output.get('blog_post_md', ''))}")
    logger.info(f"Artifacts Saved: {res.artifacts}")
    assert res.status == "success"
    logger.info("Notebook to Blog test passed!\n")

async def main():
    logger.info("Starting test suite for Agent Automation modules...")
    try:
        await test_scaffolder()
        await test_test_generator()
        await test_docs_generator()
        await test_changelog_generator()
        await test_notebook_to_blog()
        logger.info("ALL TESTS COMPLETED SUCCESSFULLY!")
    except AssertionError as ae:
        logger.error(f"Test assertion failed: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Test crashed with exception: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
