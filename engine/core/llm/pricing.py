"""
Gemini Pricing Table.

Pricing for all supported Gemini models (USD per 1 million tokens).
Updated: July 2025. Source: https://ai.google.dev/pricing

This table is used by the usage tracker to calculate cost per LLM call
and persist it to the llm_usage table for billing and analytics.

Update this file when Google changes pricing. All costs are in USD.

Note: Gemini 2.5 Flash has a context window split: <=200K tokens uses
one price, >200K tokens uses another (Tiered pricing).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """
    Pricing definition for a single Gemini model.

    All prices are in USD per 1 million tokens.

    Attributes:
        input_per_million:    Cost per million input (prompt) tokens.
        output_per_million:   Cost per million output (completion) tokens.
        context_window:       Max context window in tokens.
        supports_thinking:    Whether model has a thinking mode (thoughts_token_count).
    """
    input_per_million: float
    output_per_million: float
    context_window: int
    supports_thinking: bool = False


# Gemini model pricing table (USD / 1M tokens)
GEMINI_PRICING: dict[str, ModelPricing] = {
    # -------------------------------------------------------------------------
    # Gemini 2.5 Flash — Primary model for ShipFaster (recommended)
    # Best balance of speed + cost + quality for code generation
    # -------------------------------------------------------------------------
    "gemini-2.5-flash": ModelPricing(
        input_per_million=0.30,       # ≤200K context
        output_per_million=2.50,      # Non-thinking output
        context_window=1_048_576,
        supports_thinking=True,
    ),
    "gemini-2.5-flash-thinking": ModelPricing(
        input_per_million=3.50,       # Thinking mode input
        output_per_million=10.50,     # Thinking mode output
        context_window=1_048_576,
        supports_thinking=True,
    ),

    # -------------------------------------------------------------------------
    # Gemini 2.5 Pro — Complex reasoning tasks (docs, changelogs)
    # -------------------------------------------------------------------------
    "gemini-2.5-pro": ModelPricing(
        input_per_million=1.25,       # ≤200K context
        output_per_million=10.00,
        context_window=1_048_576,
        supports_thinking=True,
    ),

    # -------------------------------------------------------------------------
    # Gemini 2.0 Flash — Fast, low-latency for high-volume tasks
    # -------------------------------------------------------------------------
    "gemini-2.0-flash": ModelPricing(
        input_per_million=0.10,
        output_per_million=0.40,
        context_window=1_048_576,
        supports_thinking=False,
    ),
    "gemini-2.0-flash-lite": ModelPricing(
        input_per_million=0.075,
        output_per_million=0.30,
        context_window=1_048_576,
        supports_thinking=False,
    ),

    # -------------------------------------------------------------------------
    # Gemini 1.5 Flash — Legacy fallback
    # -------------------------------------------------------------------------
    "gemini-1.5-flash": ModelPricing(
        input_per_million=0.075,
        output_per_million=0.30,
        context_window=1_048_576,
        supports_thinking=False,
    ),
    "gemini-1.5-flash-8b": ModelPricing(
        input_per_million=0.0375,
        output_per_million=0.15,
        context_window=1_048_576,
        supports_thinking=False,
    ),
    "gemini-1.5-pro": ModelPricing(
        input_per_million=1.25,
        output_per_million=5.00,
        context_window=2_097_152,
        supports_thinking=False,
    ),
}

# Default model for ShipFaster — best cost/quality tradeoff for code tasks
DEFAULT_MODEL = "gemini-2.5-flash"

# Model fallback chain: if primary fails, try next in list
MODEL_FALLBACK_CHAIN: list[str] = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    thoughts_tokens: int = 0,
) -> float:
    """
    Calculate the cost of an LLM call in USD.

    Args:
        model:             Model name (e.g. "gemini-2.5-flash").
        prompt_tokens:     Number of input tokens consumed.
        completion_tokens: Number of output tokens generated.
        thoughts_tokens:   Number of thinking tokens (if applicable).

    Returns:
        Total cost in USD, rounded to 8 decimal places.
        Returns 0.0 if the model is not in the pricing table.
    """
    pricing = GEMINI_PRICING.get(model)
    if pricing is None:
        return 0.0

    input_cost = (prompt_tokens / 1_000_000) * pricing.input_per_million
    output_cost = (completion_tokens / 1_000_000) * pricing.output_per_million
    # Thinking tokens billed as output tokens on Gemini 2.5
    thoughts_cost = (thoughts_tokens / 1_000_000) * pricing.output_per_million

    return round(input_cost + output_cost + thoughts_cost, 8)


def get_context_window(model: str) -> int:
    """
    Return the context window size for a model.

    Args:
        model: Model name.

    Returns:
        Context window in tokens, or 1_000_000 as safe default.
    """
    pricing = GEMINI_PRICING.get(model)
    return pricing.context_window if pricing else 1_000_000
