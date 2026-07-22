"""OpenRouter provider implementation."""

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

logger = logging.getLogger(__name__)


class OpenRouterProvider(ProviderBase):
    """OpenRouter LLM provider implementation."""

    # Model configurations - using common models available on OpenRouter
    MODEL_MAX_TOKENS = {
        "anthropic/claude-3.5-sonnet": 8192,
        "anthropic/claude-3.5-haiku": 8192,
        "anthropic/claude-3-opus": 4096,
        "openai/gpt-4o": 4096,
        "openai/gpt-4o-mini": 16384,
        "openai/gpt-4-turbo": 4096,
        "google/gemini-pro-1.5": 8192,
        "google/gemini-flash-1.5": 8192,
        "meta-llama/llama-3.1-405b-instruct": 4096,
        "meta-llama/llama-3.1-70b-instruct": 4096,
        "meta-llama/llama-3.1-8b-instruct": 4096,
        "mistralai/mistral-large": 8192,
        "mistralai/mistral-nemo": 8192,
        "qwen/qwen-2.5-72b-instruct": 8192,
        "qwen/qwen-2.5-7b-instruct": 8192,
    }

    # Pricing per 1K tokens (approximate, varies by model on OpenRouter)
    MODEL_PRICING = {
        "anthropic/claude-3.5-sonnet": {"prompt": 3.0, "completion": 15.0},
        "anthropic/claude-3.5-haiku": {"prompt": 0.25, "completion": 1.25},
        "anthropic/claude-3-opus": {"prompt": 15.0, "completion": 75.0},
        "openai/gpt-4o": {"prompt": 2.5, "completion": 10.0},
        "openai/gpt-4o-mini": {"prompt": 0.15, "completion": 0.6},
        "openai/gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
        "google/gemini-pro-1.5": {"prompt": 1.25, "completion": 5.0},
        "google/gemini-flash-1.5": {"prompt": 0.075, "completion": 0.3},
        "meta-llama/llama-3.1-405b-instruct": {"prompt": 3.0, "completion": 3.0},
        "meta-llama/llama-3.1-70b-instruct": {"prompt": 0.88, "completion": 0.88},
        "meta-llama/llama-3.1-8b-instruct": {"prompt": 0.18, "completion": 0.18},
        "mistralai/mistral-large": {"prompt": 2.0, "completion": 6.0},
        "mistralai/mistral-nemo": {"prompt": 0.15, "completion": 0.15},
        "qwen/qwen-2.5-72b-instruct": {"prompt": 0.9, "completion": 0.9},
        "qwen/qwen-2.5-7b-instruct": {"prompt": 0.08, "completion": 0.08},
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url or "https://openrouter.ai/api/v1"
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key = config.api_key
        self._token_usage = TokenUsage()
        self._cost_estimate = 0.0

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def default_model(self) -> str:
        return self.config.default_model or "openai/gpt-4o-mini"

    async def _initialize_client(self) -> None:
        """Initialize aiohttp client session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://toolbridge-mcp-server",
                "X-Title": "ToolBridge MCP Server",
            }
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            )
        self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure client is initialized."""
        if not self._initialized:
            await self._initialize_client()

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using OpenRouter API."""
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
                        raise Exception(f"OpenRouter API error {response.status}: {error_text}")
            except aiohttp.ClientError as e:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception(f"OpenRouter request failed after retries: {e}")

        raise Exception("OpenRouter request failed after all retries")

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        """Stream text generation using OpenRouter API."""
        await self._ensure_initialized()
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
                raise Exception(f"OpenRouter streaming error {response.status}: {error_text}")

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
        """Check OpenRouter API health."""
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
        """Get available OpenRouter models."""
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
                            max_tokens=self.MODEL_MAX_TOKENS.get(model_name, 4096),
                            cost_per_1k_prompt=self.MODEL_PRICING.get(model_name, {}).get("prompt", 0.0),
                            cost_per_1k_completion=self.MODEL_PRICING.get(model_name, {}).get("completion", 0.0),
                            supports_streaming=True,
                            context_window=self.MODEL_MAX_TOKENS.get(model_name, 4096),
                        ))
                    return models
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
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