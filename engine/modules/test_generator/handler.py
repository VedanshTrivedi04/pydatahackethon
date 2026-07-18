import ast
import logging
from typing import List, Dict, Any, Tuple
from engine.core.models import ModuleResult
from engine.core import storage
from engine.core import llm_client
from engine.core import sandbox
from engine.prompts.test_generator import TEST_GENERATION_SYSTEM_PROMPT, TEST_FIXER_SYSTEM_PROMPT

logger = logging.getLogger("engine.modules.test_generator")

def analyze_code_structure(code: str) -> List[str]:
    """
    Parses Python code using AST to find functions, classes, and logic branches
    (if statements, try/except blocks, for/while loops).
    """
    try:
        tree = ast.parse(code)
    except Exception as e:
        return [f"Syntax error in source file: {str(e)}"]

    branches = []

    class CodeAnalyzer(ast.NodeVisitor):
        def __init__(self):
            self.current_context = []

        def get_current_context(self) -> str:
            return " -> ".join(self.current_context) if self.current_context else "module level"

        def visit_ClassDef(self, node):
            self.current_context.append(f"class {node.name}")
            self.generic_visit(node)
            self.current_context.pop()

        def visit_FunctionDef(self, node):
            ctx = self.get_current_context()
            args_list = [a.arg for a in node.args.args]
            branches.append(f"Function: `{node.name}` under `{ctx}` with arguments `{args_list}`")
            self.current_context.append(f"func {node.name}")
            self.generic_visit(node)
            self.current_context.pop()

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_If(self, node):
            ctx = self.get_current_context()
            try:
                cond_str = ast.unparse(node.test)
            except Exception:
                cond_str = "expression"
            branches.append(f"Conditional Branch (If) in `{ctx}` testing condition: `{cond_str}`")
            self.generic_visit(node)

        def visit_Try(self, node):
            ctx = self.get_current_context()
            handlers = []
            for handler in node.handlers:
                if handler.type:
                    try:
                        handlers.append(ast.unparse(handler.type))
                    except Exception:
                        handlers.append("Exception")
                else:
                    handlers.append("generic exception")
            branches.append(f"Exception Handling Branch (Try-Except) in `{ctx}` catching errors: `{handlers}`")
            self.generic_visit(node)

        def visit_For(self, node):
            ctx = self.get_current_context()
            branches.append(f"Loop Branch (For) in `{ctx}` iterating over loop")
            self.generic_visit(node)

        def visit_While(self, node):
            ctx = self.get_current_context()
            branches.append(f"Loop Branch (While) in `{ctx}` checking loop condition")
            self.generic_visit(node)

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)
    return branches

async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
    """
    Test Generator module handler.
    Parses code structure, requests LLM to write pytest tests targeting all branch scenarios,
    runs the code in an isolated sandbox, retries once on failure, and stores the results.
    
    Payload shape:
    {
        "file_content": str,   # the python code under test
        "repo_context": str    # optional description/context of repository
    }
    """
    file_content = payload.get("file_content", "")
    repo_context = payload.get("repo_context", "Python API Module")
    
    if not file_content.strip():
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error="Missing required 'file_content' in payload."
        )

    try:
        # 1. AST Analysis
        logger.info("Parsing source code structure using AST...")
        branches_found = analyze_code_structure(file_content)
        
        # 2. Build detailed prompt with branches list
        branches_formatted = "\n".join([f"- {b}" for b in branches_found])
        user_message_content = f"""Here is the Python source code under test:
```python
{file_content}
```

Here is the context of the repository:
{repo_context}

Here are the specific functions and branches that MUST be covered by your tests:
{branches_formatted}

Please write the complete pytest code covering these requirements.
"""
        
        # 3. Call LLM for first attempt
        logger.info("Requesting LLM to generate pytest code...")
        test_code = await llm_client.complete(
            tenant_id=tenant_id,
            job_id=job_id,
            system=TEST_GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message_content}]
        )
        
        # Clean up any potential markdown backticks that the LLM might have returned despite instructions
        test_code_cleaned = test_code
        if "```" in test_code:
            # Strip code blocks
            lines = test_code.split("\n")
            cleaned_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not line.strip().startswith("```"):
                    cleaned_lines.append(line)
            test_code_cleaned = "\n".join(cleaned_lines)
            
        test_code_cleaned = test_code_cleaned.strip()

        # 4. Sandbox validation (First run)
        logger.info("Executing generated tests in the sandbox...")
        additional_files = {"target_module.py": file_content}
        passed, sandbox_output = sandbox.execute(test_code_cleaned, additional_files)
        
        # 5. Retry once if failed
        if not passed:
            logger.warning("Sandbox run failed. Retrying test generation with error feedback...")
            fixer_prompt = TEST_FIXER_SYSTEM_PROMPT.format(
                source_code=file_content,
                test_code=test_code_cleaned,
                error_output=sandbox_output
            )
            
            test_code_retry = await llm_client.complete(
                tenant_id=tenant_id,
                job_id=job_id,
                system=fixer_prompt,
                messages=[{"role": "user", "content": "Please generate the fixed pytest code."}]
            )
            
            # Clean up markdown wrap from retry
            if "```" in test_code_retry:
                lines = test_code_retry.split("\n")
                cleaned_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    cleaned_lines.append(line)
                test_code_cleaned = "\n".join(cleaned_lines)
            else:
                test_code_cleaned = test_code_retry
                
            test_code_cleaned = test_code_cleaned.strip()
            
            # Re-execute in sandbox
            logger.info("Executing re-generated tests in the sandbox...")
            passed, sandbox_output = sandbox.execute(test_code_cleaned, additional_files)

        # 6. Save tests to storage
        artifact_key = storage.save_artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name="test_generated.py",
            file_content=test_code_cleaned.encode("utf-8"),
            content_type="text/plain"
        )
        
        status = "success" if passed else "partial"
        error_msg = None if passed else "Sandbox test execution failed."
        
        return ModuleResult(
            status=status,
            output={
                "test_code": test_code_cleaned,
                "sandbox_passed": passed,
                "sandbox_output": sandbox_output,
                "branches_covered": branches_found,
                "artifact_key": artifact_key
            },
            artifacts=[artifact_key],
            error=error_msg
        )
        
    except Exception as e:
        logger.error(f"Error in test generator module execution: {str(e)}")
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error=str(e)
        )
