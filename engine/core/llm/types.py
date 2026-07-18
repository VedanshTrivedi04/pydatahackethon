"""
LLM Call Result — Domain Value Object.

Returned by every LLMClient.generate() call.
Contains the text, token counts, cost, latency, and model used.

This is what Dev 1's module handlers receive back from the LLM client.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMCallResult:
    """
    Immutable result of a single LLM generation call.

    Attributes:
        text:              The generated text content.
        model:             Actual model name used (may differ from requested if fallback triggered).
        prompt_tokens:     Input token count (from usage_metadata).
        completion_tokens: Output token count (from usage_metadata).
        thoughts_tokens:   Thinking token count (Gemini 2.5+ only, else 0).
        total_tokens:      Sum of all token counts.
        cost_usd:          Estimated cost in USD.
        latency_ms:        Wall-clock latency in milliseconds.
        finish_reason:     Why generation stopped (STOP, MAX_TOKENS, SAFETY, etc.).
        usage_record_id:   UUID of the persisted llm_usage record (for audit).
        metadata:          Additional model-specific metadata.
    """
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    thoughts_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    finish_reason: str
    usage_record_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMGenerationConfig:
    """
    Configuration for a single LLM generation request.

    Attributes:
        system_prompt:       System instruction to prepend.
        temperature:         Sampling temperature (0.0–2.0). Lower = more deterministic.
        max_output_tokens:   Max tokens to generate (None = model default).
        top_p:               Nucleus sampling probability.
        top_k:               Top-K sampling.
        response_mime_type:  Force JSON output with "application/json".
        thinking_budget:     Token budget for Gemini 2.5 thinking mode (0 = disable thinking).
    """
    system_prompt: str | None = None
    temperature: float = 0.3        # Low temp for code generation (deterministic)
    max_output_tokens: int | None = None
    top_p: float = 0.95
    top_k: int = 40
    response_mime_type: str | None = None     # "application/json" for structured output
    thinking_budget: int | None = None        # None = let model decide
