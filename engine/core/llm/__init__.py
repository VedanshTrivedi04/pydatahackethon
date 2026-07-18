"""
LLM package exports.

Usage in modules (Dev 1):

    from engine.core.llm import get_llm_client, LLMGenerationConfig

    client = get_llm_client()

    result = await client.generate(
        prompt="Write unit tests for this function...",
        config=LLMGenerationConfig(
            system_prompt="You are an expert Python testing engineer.",
            temperature=0.2,
        ),
        job_id=job_id,
        tenant_id=tenant_id,
        session=session,
    )

    print(result.text)           # Generated code
    print(result.cost_usd)       # e.g. 0.000345
    print(result.prompt_tokens)  # e.g. 1200

For JSON output:

    data, result = await client.generate_json(
        prompt="Extract these fields as JSON: ...",
        config=LLMGenerationConfig(temperature=0.1),
    )
"""

from engine.core.llm.client import LLMClient, get_llm_client
from engine.core.llm.types import LLMCallResult, LLMGenerationConfig
from engine.core.llm.pricing import (
    DEFAULT_MODEL,
    MODEL_FALLBACK_CHAIN,
    GEMINI_PRICING,
    calculate_cost,
)
from engine.core.llm.usage_tracker import LLMUsageTracker

__all__ = [
    "LLMClient",
    "get_llm_client",
    "LLMCallResult",
    "LLMGenerationConfig",
    "DEFAULT_MODEL",
    "MODEL_FALLBACK_CHAIN",
    "GEMINI_PRICING",
    "calculate_cost",
    "LLMUsageTracker",
]
