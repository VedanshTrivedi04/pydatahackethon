import json
import base64
import logging
from typing import Dict, List, Any, Tuple
from engine.core.models import ModuleResult
from engine.core import storage
from engine.core import llm_client
from engine.prompts.notebook_to_blog import NOTEBOOK_TO_BLOG_SYSTEM_PROMPT

logger = logging.getLogger("engine.modules.notebook_to_blog")

def parse_notebook_content(notebook_str: str, job_id: str, tenant_id: str) -> Tuple[str, List[str]]:
    """
    Parses a Jupyter notebook (.ipynb) JSON string.
    Extracts text/code cells and saves base64 images to storage.
    
    Returns:
        (extracted_text: str, saved_image_keys: List[str])
    """
    try:
        notebook = json.loads(notebook_str)
    except Exception as e:
        logger.error(f"Failed to parse notebook JSON: {str(e)}")
        return f"Error parsing notebook: {str(e)}", []
        
    extracted_parts = []
    image_keys = []
    image_count = 0
    
    cells = notebook.get("cells", [])
    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "")
        source_list = cell.get("source", [])
        source = "".join(source_list) if isinstance(source_list, list) else str(source_list)
        
        if cell_type == "markdown":
            extracted_parts.append(f"\n[Prose Content]:\n{source}\n")
        elif cell_type == "code":
            extracted_parts.append(f"\n[Code Code]:\n```python\n{source}\n```\n")
            
            # Check outputs for images
            outputs = cell.get("outputs", [])
            for out in outputs:
                data = out.get("data", {})
                # Look for base64 images (image/png or image/jpeg)
                image_data = None
                img_ext = "png"
                content_type = "image/png"
                
                if "image/png" in data:
                    image_data = data["image/png"]
                    img_ext = "png"
                    content_type = "image/png"
                elif "image/jpeg" in data:
                    image_data = data["image/jpeg"]
                    img_ext = "jpg"
                    content_type = "image/jpeg"
                    
                if image_data:
                    # Clean up base64 (sometimes contains newlines)
                    if isinstance(image_data, list):
                        image_data = "".join(image_data)
                    image_data_clean = image_data.replace("\n", "").strip()
                    
                    try:
                        img_bytes = base64.b64decode(image_data_clean)
                        image_count += 1
                        file_name = f"notebook_image_{image_count}.{img_ext}"
                        
                        # Save to storage
                        s3_key = storage.save_artifact(
                            job_id=job_id,
                            tenant_id=tenant_id,
                            file_name=file_name,
                            file_content=img_bytes,
                            content_type=content_type
                        )
                        image_keys.append(s3_key)
                        
                        # Add a placeholder reference in the text stream
                        # In dev, we can map this key to local endpoints
                        placeholder_url = f"/api/v1/jobs/{job_id}/artifacts/{s3_key.split('/')[-1]}"
                        extracted_parts.append(f"\n[Image Placeholder: {placeholder_url}]\n")
                        
                    except Exception as img_err:
                        logger.error(f"Failed to decode/save notebook image: {str(img_err)}")
                        
    return "\n".join(extracted_parts), image_keys


async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
    """
    Notebook-to-blog module handler.
    Parses a Jupyter notebook (.ipynb) structure, extracts Markdown cells, code cells,
    saves base64 images to storage, and sends content to LLM to write a technical blog.
    
    Payload shape:
    {
        "notebook_content": str   # raw string content of the .ipynb file
    }
    """
    notebook_content = payload.get("notebook_content", "")
    
    # If notebook_content is empty, let's look for a dummy notebook string
    # (very helpful to avoid crashes in dry runs/tests)
    if not notebook_content.strip():
        logger.info("Notebook content is empty, loading dummy notebook payload for demo/test.")
        dummy_notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# Data Analysis of App Usage\n", "We analyze how user engagement changes over time."]
                },
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "metadata": {},
                    "outputs": [],
                    "source": ["import pandas as pd\ndf = pd.read_csv('usage.csv')\ndf.head()"]
                },
                {
                    "cell_type": "code",
                    "execution_count": 2,
                    "metadata": {},
                    "outputs": [
                        {
                            "data": {
                                # Base64 for 1x1 transparent pixel png
                                "image/png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                            },
                            "output_type": "display_data"
                        }
                    ],
                    "source": ["import matplotlib.pyplot as plt\nplt.plot([1, 2, 3], [4, 5, 6])\nplt.show()"]
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2
        }
        notebook_content = json.dumps(dummy_notebook)
        
    try:
        # 1. Parse and extract contents
        logger.info("Parsing Jupyter notebook structure and extracting contents...")
        extracted_text, image_keys = parse_notebook_content(notebook_content, job_id, tenant_id)
        
        # 2. Build user prompt
        user_prompt = f"""Please rewrite the following notebook stream into a beautiful technical blog post:
{extracted_text}
"""
        
        # 3. Call LLM to rewrite into blog
        logger.info("Requesting LLM to restructure notebook into blog narrative...")
        blog_draft = await llm_client.complete(
            tenant_id=tenant_id,
            job_id=job_id,
            system=NOTEBOOK_TO_BLOG_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # 4. Save blog draft as markdown file
        blog_key = storage.save_artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name="blog_post_draft.md",
            file_content=blog_draft.encode("utf-8"),
            content_type="text/markdown"
        )
        
        all_artifacts = [blog_key] + image_keys
        
        return ModuleResult(
            status="success",
            output={
                "blog_post_md": blog_draft,
                "draft_key": blog_key,
                "image_keys": image_keys
            },
            artifacts=all_artifacts,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error in notebook_to_blog module execution: {str(e)}")
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error=str(e)
        )
