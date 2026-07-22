"""Cerebras provider implementation."""

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Optional

import aiohttp

from mcp_server.providers.base import (
    ProviderBase,
    ProviderConfig,
    GenerationRequest,
    GenerationResponse,
    HealthCheckResult,
    ModelInfo,
    TokenUsage,
)
from mcp_server.providers.base import GenerationResponse

logger = logging.getLogger(__name__)


class CerebrasProvider(ProviderBase):
    """Cerebras LLM provider implementation."""

    # Model configurations
    MODEL_MAX_TOKENS = {
        "llama3.1-8b": 8192,
        "llama3.1-70b": 8192,
        "llama3.1-405b": 8192,
        "llama-3.3-70b": 8192,
    }

    MODEL_PRICING = {
        "llama3.1-8b": {"prompt": 0.0001, "completion": 0.0001},
        "llama3.1-70b": {"prompt": 0.0006, "completion": 0.0006},
        "llama3.1-405b": {"prompt": 0.004, "completion": 0.004},
        "llama-3.3-70b": {"prompt": 0.0006, "completion": 0.0006},
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url or "https://api.cerebras.ai/v1"
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key = config.api_key
        self._token_usage = TokenUsage()
        self._cost_estimate = 0.0

    @property
    def name(self) -> str:
        return "cerebras"

    @property
    def default_model(self) -> str:
        return self.config.default_model or "llama3.1-70b"

    async def _initialize_client(self) -> None:
        """Initialize aiohttp client session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            )
        self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure client is initialized."""
        if not self._initialized:
            await self._initialize_client()

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Cerebras API."""
        await self._ensure_initialized()
        model = request.model or self.default_model

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens or self.MODEL_MAX_TOKENS.get(model, 4096),
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.stop:
            payload["stop"] = request.stop
        if request.extra_params:
            payload.update(request.extra_params)

        start_time = time.perf_counter()

        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._session.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        finish_reason = data["choices"][0].get("finish_reason")

                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                        pricing = self.MODEL_PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
                        cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1000

                        latency_ms = (time.perf_counter() - start_time) * 1000

                        self._update_token_usage(prompt_tokens, completion_tokens, cost)

                        return GenerationResponse(
                            text=content,
                            model=model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            cost_estimate=cost,
                            finish_reason=finish_reason,
                            latency_ms=latency_ms,
                            provider=self.name,
                        )
                    elif response.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"Cerebras API error {response.status}: {error_text}")
            except aiohttp.ClientError as e:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception(f"Cerebras request failed after retries: {e}")

        raise Exception("Cerebras request failed after all retries")

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        """Stream text generation using Cerebras API."""
        await self._ensure_initialized()
        model = request.model or self.default_model

        payload = {
            "model": request.model or self.default_model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens or self.MODEL_MAX_TOKENS.get(model, 4096),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True,
        }

        if request.stop:
            payload["stop"] = request.stop
        if request.extra_params:
            payload.update(request.extra_params)

        async with self._session.post(
            f"{self._base_url}/chat/completions",
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Cerebras streaming error {response.status}: {error_text}")

            async for line in response.content:
                line = line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("choices") and data["choices"][0].get("delta", {}).get("content"):
                            yield data["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> HealthCheckResult:
        """Check Cerebras API health."""
        start_time = time.perf_counter()
        try:
            await self._ensure_initialized()
            async with self._session.get(
                f"{self._base_url}/models",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                latency_ms = (time.perf_counter() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return HealthCheckResult(
                        healthy=True,
                        latency_ms=latency_ms,
                        available_models=models,
                    )
                else:
                    return HealthCheckResult(
                        healthy=False,
                        latency_ms=latency_ms,
                        error=f"HTTP {response.status}",
                    )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return HealthCheckResult(
                healthy=False,
                latency_ms=latency_ms,
                error=str(e),
            )

    async def available_models(self) -> list[ModelInfo]:
        """Get available Cerebras models."""
        try:
            await self._ensure_initialized()
            async with self._session.get(
                f"{self._base_url}/models",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = []
                    for m in data.get("data", []):
                        model_name = m["id"]
                        models.append(ModelInfo(
                            name=model_name,
                            max_tokens=self.MODEL_MAX_TOKENS.get(model_name, 8192),
                            cost_per_1k_prompt=self.MODEL_PRICING.get(model_name, {}).get("prompt", 0.0),
                            cost_per_1k_completion=self.MODEL_PRICING.get(model_name, {}).get("completion", 0.0),
                            supports_streaming=True,
                            context_window=self.MODEL_MAX_TOKENS.get(model_name, 8192),
                        ))
                    return models
        except Exception as e:
            logger.error(f"Failed to fetch Cerebras models: {e}")
        return []

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)."""
        return len(text) // 4

    async def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost for generation request."""
        model = request.model or self.default_model
        prompt_tokens = await self.count_tokens(request.prompt, model)
        estimated_completion = request.max_tokens or 100
        pricing = self.MODEL_PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
        return (prompt_tokens * pricing["prompt"] + estimated_completion * pricing["completion"]) / 1000

    def _update_token_usage(self, prompt_tokens: int, completion_tokens: int, cost: float) -> None:
        """Update internal token usage tracking."""
        self._token_usage.prompt_tokens += prompt_tokens
        self._token_usage.completion_tokens += completion_tokens
        self._token_usage.total_tokens += prompt_tokens + completion_tokens
        self._token_usage.cost_estimate += cost
        self._cost_estimate += cost

    def get_token_usage(self) -> TokenUsage:
        """Get current token usage statistics."""
        return self._token_usage

    def get_cost_estimate(self) -> float:
        """Get total cost estimate."""
        return self._cost_estimate

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._initialized = False