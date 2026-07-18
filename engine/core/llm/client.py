"""
Gemini LLM Client — Core Infrastructure Layer.

The single, centralized wrapper around Google's `google-genai` SDK.
ALL LLM calls in ShipFaster go through this class.

NO module (Dev 1) should ever import google.genai directly —
they always call LLMClient.generate() or LLMClient.generate_json().

Features:
- Async-native (uses client.aio.models.generate_content)
- Automatic model fallback chain (2.5-flash → 2.0-flash → 1.5-flash)
- Tenacity-based retry with exponential backoff on transient errors
- Token counting + cost calculation on every call
- Automatic usage persistence to llm_usage table
- Structured JSON output mode (response_mime_type=application/json)
- System prompt support
- Configurable temperature, max_tokens, top_p, top_k
- Thinking budget control for Gemini 2.5

Dependencies:
    pip install google-genai tenacity

Settings required:
    GEMINI_API_KEY in .env (loaded via engine.config.settings)
"""

import time
import uuid
from typing import Any

import tenacity
from google import genai
from google.genai import types as genai_types
from google.genai.errors import APIError, ClientError, ServerError

from engine.core.llm.pricing import (
    DEFAULT_MODEL,
    MODEL_FALLBACK_CHAIN,
    calculate_cost,
    get_context_window,
)
from engine.core.llm.types import LLMCallResult, LLMGenerationConfig
from engine.utils.exceptions import LLMError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Transient vs Permanent Errors
# ---------------------------------------------------------------------------
# Retry only on transient (server-side) errors.
# Never retry on client errors (bad prompt, bad API key, quota exhausted).

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an exception warrants a retry."""
    if isinstance(exc, ServerError):
        return True
    if isinstance(exc, APIError) and hasattr(exc, "status_code"):
        return exc.status_code in RETRYABLE_STATUS_CODES
    return False


class LLMClient:
    """
    Async Gemini LLM Client for ShipFaster.

    Provides a clean, high-level interface for LLM generation
    with automatic retry, fallback, token tracking, and cost calculation.

    This client is NOT request-scoped — it is a long-lived singleton
    initialized at worker startup. It does not hold DB sessions.
    Usage persistence is done by injecting a session at call time.

    Instantiation:
        client = LLMClient()                            # Uses settings.GEMINI_API_KEY
        client = LLMClient(api_key="custom-key")        # Override API key

    Usage:
        result = await client.generate(
            prompt="Write a FastAPI route for user registration",
            config=LLMGenerationConfig(temperature=0.2),
        )
        print(result.text)
        print(f"Cost: ${result.cost_usd:.6f}")
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize the Gemini client.

        Args:
            api_key: Optional API key override. Falls back to settings.
        """
        from engine.config.settings import get_settings
        settings = get_settings()

        resolved_key = api_key or settings.llm.gemini_api_key
        if not resolved_key:
            raise LLMError(
                "GEMINI_API_KEY is not configured. "
                "Set GEMINI__GEMINI_API_KEY in your .env file."
            )

        self._client = genai.Client(api_key=resolved_key)
        self._default_model = getattr(settings.llm, "default_model", DEFAULT_MODEL)

        logger.info(
            "llm.client_initialized",
            default_model=self._default_model,
        )

    # -------------------------------------------------------------------------
    # Primary API
    # -------------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        config: LLMGenerationConfig | None = None,
        job_id: str | None = None,
        tenant_id: str | None = None,
        session: Any | None = None,
    ) -> LLMCallResult:
        """
        Generate text from a prompt using Gemini.

        Automatically retries on transient errors and falls back to
        cheaper/faster models if the primary model is unavailable.

        Args:
            prompt:    The user prompt text.
            model:     Model to use (default: gemini-2.5-flash).
            config:    Generation config (temperature, max_tokens, etc.).
            job_id:    Job UUID string — for usage tracking.
            tenant_id: Tenant UUID string — for usage tracking.
            session:   Optional AsyncSession for persisting usage record.
                       If None, usage is logged but not persisted.

        Returns:
            LLMCallResult with text, tokens, cost, latency.

        Raises:
            LLMError: If all retry attempts and all fallbacks fail.
        """
        effective_config = config or LLMGenerationConfig()
        model_chain = self._build_model_chain(model)

        last_exception: Exception | None = None

        for attempt_model in model_chain:
            try:
                result = await self._generate_with_retry(
                    model=attempt_model,
                    prompt=prompt,
                    config=effective_config,
                )
                # Persist usage record
                if session is not None:
                    result = await self._persist_usage(
                        result=result,
                        session=session,
                        job_id=job_id,
                        tenant_id=tenant_id,
                    )

                logger.info(
                    "llm.call_success",
                    model=result.model,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    cost_usd=result.cost_usd,
                    latency_ms=result.latency_ms,
                    job_id=job_id,
                )
                return result

            except LLMError as e:
                last_exception = e
                logger.warning(
                    "llm.model_failed_trying_fallback",
                    failed_model=attempt_model,
                    error=str(e),
                    next_in_chain=model_chain[model_chain.index(attempt_model) + 1]
                    if model_chain.index(attempt_model) < len(model_chain) - 1
                    else "none",
                )
                continue  # Try next model in fallback chain

        # All models failed
        raise LLMError(
            f"All LLM models failed. Last error: {last_exception}"
        )

    async def generate_json(
        self,
        prompt: str,
        model: str | None = None,
        config: LLMGenerationConfig | None = None,
        job_id: str | None = None,
        tenant_id: str | None = None,
        session: Any | None = None,
    ) -> tuple[dict[str, Any], LLMCallResult]:
        """
        Generate structured JSON output from Gemini.

        Forces `response_mime_type="application/json"` in generation config.
        Parses the JSON response and returns it alongside the full call result.

        Args:
            prompt:    Prompt that instructs Gemini to output JSON.
            model:     Model to use.
            config:    Generation config (response_mime_type is overridden to application/json).
            job_id:    Job UUID for usage tracking.
            tenant_id: Tenant UUID for usage tracking.
            session:   Optional DB session for persistence.

        Returns:
            Tuple of (parsed_dict, LLMCallResult).

        Raises:
            LLMError: If generation fails or response is not valid JSON.
        """
        import json

        json_config = LLMGenerationConfig(
            system_prompt=config.system_prompt if config else None,
            temperature=config.temperature if config else 0.1,  # Low temp for JSON
            max_output_tokens=config.max_output_tokens if config else None,
            top_p=config.top_p if config else 0.95,
            top_k=config.top_k if config else 40,
            response_mime_type="application/json",
            thinking_budget=config.thinking_budget if config else None,
        )

        result = await self.generate(
            prompt=prompt,
            model=model,
            config=json_config,
            job_id=job_id,
            tenant_id=tenant_id,
            session=session,
        )

        try:
            parsed = json.loads(result.text)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Gemini returned invalid JSON. "
                f"Parse error: {e}. "
                f"Raw response (first 500 chars): {result.text[:500]}"
            ) from e

        return parsed, result

    async def count_tokens(self, prompt: str, model: str | None = None) -> int:
        """
        Count tokens in a prompt without generating a response.

        Useful for validating prompt length before making a full call.

        Args:
            prompt: The prompt to count tokens for.
            model:  Model to use for counting (token counts vary by model).

        Returns:
            Token count (int).
        """
        effective_model = model or self._default_model
        try:
            response = await self._client.aio.models.count_tokens(
                model=effective_model,
                contents=prompt,
            )
            return response.total_tokens or 0
        except Exception as e:
            logger.warning("llm.count_tokens_failed", error=str(e))
            # Estimate: ~4 chars per token
            return len(prompt) // 4

    # -------------------------------------------------------------------------
    # Internal: Retry Logic
    # -------------------------------------------------------------------------

    async def _generate_with_retry(
        self,
        model: str,
        prompt: str,
        config: LLMGenerationConfig,
    ) -> LLMCallResult:
        """
        Call Gemini API with Tenacity retry on transient failures.

        Retry policy:
        - 3 total attempts
        - Exponential backoff: 2s → 4s → 8s (with jitter)
        - Only retries on ServerError (5xx) and 429 (rate limit)
        - Never retries on ClientError (4xx) — bad prompt, safety block, etc.
        """

        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=30)
            + tenacity.wait_random(0, 1),  # Jitter prevents thundering herd
            retry=tenacity.retry_if_exception(_is_retryable),
            reraise=True,
        )
        async def _call() -> LLMCallResult:
            return await self._single_call(model=model, prompt=prompt, config=config)

        try:
            return await _call()
        except (ClientError, APIError) as e:
            # Convert SDK errors to our domain error
            raise LLMError(f"Gemini API error [{model}]: {str(e)}") from e
        except tenacity.RetryError as e:
            raise LLMError(
                f"Gemini [{model}] failed after all retries: {str(e.last_attempt.exception())}"
            ) from e

    async def _single_call(
        self,
        model: str,
        prompt: str,
        config: LLMGenerationConfig,
    ) -> LLMCallResult:
        """
        Execute a single, non-retrying Gemini API call.

        Args:
            model:  Model name string.
            prompt: User prompt.
            config: Generation configuration.

        Returns:
            LLMCallResult with full metadata.
        """
        # Build GenerateContentConfig from our domain config
        generation_config = self._build_generation_config(config)

        # Build contents list (with optional system instruction)
        contents: list[genai_types.Content | str] = [prompt]

        start_ts = time.perf_counter()

        # Async call via client.aio.models.generate_content
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=generation_config,
        )

        latency_ms = int((time.perf_counter() - start_ts) * 1000)

        # Extract text
        text = response.text or ""

        # Extract usage metadata
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
        thoughts_tokens = getattr(usage, "thoughts_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or (
            prompt_tokens + completion_tokens + thoughts_tokens
        )

        # Extract finish reason
        finish_reason = "UNKNOWN"
        if response.candidates:
            fr = response.candidates[0].finish_reason
            finish_reason = str(fr) if fr else "UNKNOWN"

        # Calculate cost
        cost = calculate_cost(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thoughts_tokens=thoughts_tokens,
        )

        return LLMCallResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thoughts_tokens=thoughts_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )

    # -------------------------------------------------------------------------
    # Internal: Usage Persistence
    # -------------------------------------------------------------------------

    async def _persist_usage(
        self,
        result: LLMCallResult,
        session: Any,
        job_id: str | None,
        tenant_id: str | None,
    ) -> LLMCallResult:
        """
        Persist an LLM usage record to the llm_usage table.

        Updates the result with the usage_record_id for audit trail.

        Args:
            result:    The LLMCallResult to persist.
            session:   Async SQLAlchemy session.
            job_id:    Job UUID string (nullable).
            tenant_id: Tenant UUID string (nullable).

        Returns:
            Updated LLMCallResult with usage_record_id set.
        """
        try:
            from engine.core.models.llm import LLMUsage
            import uuid as _uuid

            usage_record = LLMUsage(
                tenant_id=_uuid.UUID(tenant_id) if tenant_id else None,
                job_id=_uuid.UUID(job_id) if job_id else None,
                provider="gemini",
                model=result.model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
                finish_reason=result.finish_reason,
                metadata={
                    "thoughts_tokens": result.thoughts_tokens,
                },
            )
            session.add(usage_record)
            await session.flush()

            # Return new LLMCallResult with usage_record_id set
            import dataclasses
            return dataclasses.replace(
                result,
                usage_record_id=str(usage_record.id),
            )

        except Exception as e:
            logger.error("llm.persist_usage_failed", error=str(e))
            # Usage persistence failure does NOT fail the LLM call
            return result

    # -------------------------------------------------------------------------
    # Internal: Helper Builders
    # -------------------------------------------------------------------------

    def _build_model_chain(self, requested_model: str | None) -> list[str]:
        """
        Build the model fallback chain starting from the requested model.

        If a specific model is requested, tries it first, then falls back.
        If no model is requested, uses the full default fallback chain.

        Args:
            requested_model: Optional specific model name.

        Returns:
            Ordered list of models to try.
        """
        if requested_model:
            # If requested model is in fallback chain, start from it
            chain = MODEL_FALLBACK_CHAIN[:]
            if requested_model in chain:
                start_idx = chain.index(requested_model)
                return chain[start_idx:]
            else:
                # Custom model not in chain — try it first, then chain
                return [requested_model] + MODEL_FALLBACK_CHAIN
        return MODEL_FALLBACK_CHAIN[:]

    def _build_generation_config(
        self, config: LLMGenerationConfig
    ) -> genai_types.GenerateContentConfig:
        """
        Convert our domain LLMGenerationConfig to the SDK's GenerateContentConfig.

        Args:
            config: Domain generation configuration.

        Returns:
            genai_types.GenerateContentConfig for SDK use.
        """
        kwargs: dict[str, Any] = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
        }

        if config.system_prompt:
            kwargs["system_instruction"] = config.system_prompt

        if config.max_output_tokens:
            kwargs["max_output_tokens"] = config.max_output_tokens

        if config.response_mime_type:
            kwargs["response_mime_type"] = config.response_mime_type

        # Thinking budget for Gemini 2.5 models
        if config.thinking_budget is not None:
            kwargs["thinking_config"] = genai_types.ThinkingConfig(
                thinking_budget=config.thinking_budget
            )

        return genai_types.GenerateContentConfig(**kwargs)


# ---------------------------------------------------------------------------
# Module-Level Singleton
# ---------------------------------------------------------------------------

_llm_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """
    Get the singleton LLMClient instance.

    Lazily initializes on first call. Reuses the same instance for all
    subsequent calls — avoids re-creating the API connection on each request.

    Returns:
        The global LLMClient instance.

    Usage:
        from engine.core.llm.client import get_llm_client
        client = get_llm_client()
        result = await client.generate("Write a test for...")
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance
