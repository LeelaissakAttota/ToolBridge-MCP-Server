"""NVIDIA provider implementation."""

from __future__ import annotations

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
)

logger = logging.getLogger(__name__)


class NvidiaProvider(ProviderBase):
    """NVIDIA provider for Nemotron and other NVIDIA models."""

    name = "nvidia"

    default_model = "nemotron-3-ultra"

    # NVIDIA model pricing (approximate, per 1k tokens)
    MODEL_PRICING = {
        "nemotron-3-ultra": {"prompt": 0.001, "completion": 0.001},
        "nemotron-3-8b": {"prompt": 0.0002, "completion": 0.0002},
        "nemotron-4-340b": {"prompt": 0.0008, "completion": 0.0008},
        "llama-3.1-70b-instruct": {"prompt": 0.0007, "completion": 0.0009},
        "llama-3.1-8b-instruct": {"prompt": 0.0001, "completion": 0.0001},
        "mistral-7b-instruct": {"prompt": 0.00015, "completion": 0.00015},
        "mixtral-8x7b-instruct": {"prompt": 0.0006, "completion": 0.0006},
    }

    # Model max tokens
    MODEL_MAX_TOKENS = {
        "nemotron-3-ultra": 4096,
        "nemotron-3-8b": 4096,
        "nemotron-4-340b": 4096,
        "llama-3.1-70b-instruct": 4096,
        "llama-3.1-8b-instruct": 4096,
        "mistral-7b-instruct": 4096,
        "mixtral-8x7b-instruct": 4096,
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = config.base_url or "https://integrate.api.nvidia.com/v1"
        self._headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        if config.extra_headers:
            self._headers.update(config.extra_headers)

    async def _initialize_client(self) -> None:
        """Initialize HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=timeout,
            )

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        await super().close()

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using NVIDIA API."""
        self._ensure_initialized()
        model = request.model or self.default_model

        start_time = time.perf_counter()

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens or self.MODEL_MAX_TOKENS.get(model, 4096),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False,
        }

        if request.stop:
            payload["stop"] = request.stop
        if request.extra_params:
            payload.update(request.extra_params)

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._session.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                ) as response:
                    if response.status == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"NVIDIA rate limited, waiting {wait_time}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"NVIDIA API error {response.status}: {error_text}")

                    data = await response.json()

                    choice = data["choices"][0]
                    content = choice["message"]["content"]
                    finish_reason = choice.get("finish_reason")

                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                    pricing = self.MODEL_PRICING.get(model, {"prompt": 0.001, "completion": 0.001})
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

            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception(f"NVIDIA request failed after retries: {last_error}")

        raise Exception(f"NVIDIA request failed: {last_error}")

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        """Stream text generation using NVIDIA API."""
        self._ensure_initialized()
        model = request.model or self.default_model

        payload = {
            "model": model,
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
                raise Exception(f"NVIDIA streaming error {response.status}: {error_text}")

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
        """Check NVIDIA API health."""
        start_time = time.perf_counter()
        try:
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
        """Get available NVIDIA models."""
        try:
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
                            max_tokens=self.MODEL_MAX_TOKENS.get(model_name, 4096),
                            cost_per_1k_prompt=self.MODEL_PRICING.get(model_name, {}).get("prompt", 0.001),
                            cost_per_1k_completion=self.MODEL_PRICING.get(model_name, {}).get("completion", 0.001),
                            supports_streaming=True,
                            context_window=self.MODEL_MAX_TOKENS.get(model_name, 4096),
                        ))
                    return models
        except Exception as e:
            logger.error(f"Failed to fetch NVIDIA models: {e}")
        return []

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)."""
        return len(text) // 4

    async def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost for generation request."""
        model = request.model or self.default_model
        prompt_tokens = await self.count_tokens(request.prompt, model)
        estimated_completion = request.max_tokens or 100
        pricing = self.MODEL_PRICING.get(model, {"prompt": 0.001, "completion": 0.001})
        return (prompt_tokens * pricing["prompt"] + estimated_completion * pricing["completion"]) / 1000