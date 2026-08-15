"""Shared OpenAI-compatible HTTP adapter for configured LLM providers."""

import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from toolbridge.providers.application.ports import BaseProvider
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderErrorCategory,
    ProviderHealthCheck,
    ProviderModel,
    TokenUsage,
)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    """Validated adapter configuration assembled by infrastructure."""

    base_url: str
    api_key: str = field(repr=False)
    default_model: str
    timeout_seconds: float
    max_tokens: int
    temperature: float
    max_prompt_bytes: int
    models_path: str
    chat_completions_path: str
    capabilities: ProviderCapabilities = field(
        default_factory=lambda: ProviderCapabilities(chat=True, streaming=True)
    )
    is_free: bool = False
    input_cost_per_million_tokens_usd: float = 0.0
    output_cost_per_million_tokens_usd: float = 0.0
    context_window: int | None = None
    reasoning_quality: float = 0.5

    @classmethod
    def from_settings(cls, settings: object) -> "OpenAICompatibleConfig":
        """Build at the credential-unwrapping infrastructure boundary."""

        api_key = getattr(settings, "api_key", None)
        default_model = getattr(settings, "default_model", None)
        if api_key is None or default_model is None:
            raise ValueError("enabled provider configuration is incomplete")
        return cls(
            base_url=str(getattr(settings, "base_url")),
            api_key=api_key.get_secret_value(),
            default_model=default_model,
            timeout_seconds=getattr(settings, "timeout_seconds"),
            max_tokens=getattr(settings, "max_tokens"),
            temperature=getattr(settings, "temperature"),
            max_prompt_bytes=getattr(settings, "max_prompt_bytes"),
            models_path=getattr(settings, "models_path"),
            chat_completions_path=getattr(settings, "chat_completions_path"),
            capabilities=(
                getattr(settings, "capabilities")
                or ProviderCapabilities(chat=True, streaming=True)
            ),
            is_free=getattr(settings, "is_free"),
            input_cost_per_million_tokens_usd=getattr(
                settings, "input_cost_per_million_tokens_usd"
            ),
            output_cost_per_million_tokens_usd=getattr(
                settings, "output_cost_per_million_tokens_usd"
            ),
            context_window=getattr(settings, "context_window"),
            reasoning_quality=getattr(settings, "reasoning_quality"),
        )

    def __post_init__(self) -> None:
        if not self.base_url.startswith("https://"):
            raise ValueError("provider base_url must use HTTPS")
        if not self.api_key:
            raise ValueError("provider api_key cannot be empty")
        if not self.default_model:
            raise ValueError("provider default_model cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("provider timeout must be greater than zero")
        if self.max_tokens <= 0 or self.max_prompt_bytes <= 0:
            raise ValueError("provider size limits must be greater than zero")
        if not 0 <= self.temperature <= 2:
            raise ValueError("provider temperature must be between 0 and 2")
        if not self.models_path.startswith("/") or not self.chat_completions_path.startswith("/"):
            raise ValueError("provider endpoint paths must start with a slash")


class OpenAICompatibleProvider(BaseProvider):
    """Normalize an OpenAI-compatible HTTP API behind the provider port."""

    def __init__(
        self,
        name: str,
        config: OpenAICompatibleConfig,
        *,
        extra_headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._name = name
        self._config = config
        self._extra_headers = dict(extra_headers or {})
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return configured normalized capabilities."""

        return self._config.capabilities

    @property
    def name(self) -> str:
        """Return the stable provider identifier."""

        return self._name

    async def initialize(self) -> None:
        """Create the asynchronous HTTP client idempotently."""

        if self._client is not None:
            return
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        self._client = httpx.AsyncClient(
            base_url=f"{self._config.base_url.rstrip('/')}/",
            timeout=httpx.Timeout(self._config.timeout_seconds),
            headers=headers,
            transport=self._transport,
        )

    async def health_check(self) -> ProviderHealthCheck:
        """Probe the configured models endpoint and report end-to-end latency."""

        started_at = perf_counter()
        await self._request_json("GET", self._config.models_path)
        return ProviderHealthCheck(
            provider=self.name,
            latency_ms=self._duration_ms(started_at),
        )

    async def list_models(self) -> tuple[ProviderModel, ...]:
        """Return normalized model identifiers from the configured endpoint."""

        payload = await self._request_json("GET", self._config.models_path)
        try:
            data = payload["data"]
            if not isinstance(data, list):
                raise TypeError
            models = tuple(
                ProviderModel(
                    id=item["id"],
                    provider=self.name,
                    capabilities=self._config.capabilities,
                    is_free=self._config.is_free,
                    input_cost_per_million_tokens_usd=(
                        self._config.input_cost_per_million_tokens_usd
                    ),
                    output_cost_per_million_tokens_usd=(
                        self._config.output_cost_per_million_tokens_usd
                    ),
                    context_window=self._config.context_window,
                    reasoning_quality=self._config.reasoning_quality,
                    discovered_at=datetime.now(UTC),
                )
                for item in data
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            )
            if len(models) != len(data):
                raise TypeError
            return models
        except (KeyError, TypeError, ValidationError) as error:
            raise ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                self.name,
            ) from error

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Send a non-streaming request and normalize the completion."""

        request_id, model, payload = self._generation_payload(request, stream=False)
        response = await self._request_json(
            "POST",
            self._config.chat_completions_path,
            json_body=payload,
        )
        self._raise_embedded_error(response)
        try:
            choices = response["choices"]
            if not isinstance(choices, list) or not choices:
                raise TypeError
            choice = choices[0]
            if not isinstance(choice, dict):
                raise TypeError
            if isinstance(choice.get("error"), dict):
                self._raise_embedded_error(choice)
            message = choice["message"]
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise TypeError
            response_model = response.get("model", model)
            if not isinstance(response_model, str) or not response_model:
                raise TypeError
            finish_reason = choice.get("finish_reason")
            if finish_reason is not None and not isinstance(finish_reason, str):
                raise TypeError
            usage = self._parse_usage(response.get("usage"))
            return GenerationResponse(
                provider=self.name,
                request_id=request_id,
                model=response_model,
                content=message["content"],
                finish_reason=finish_reason,
                usage=usage,
            )
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                self.name,
            ) from error

    async def stream_generate(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[GenerationChunk]:
        """Stream and normalize standard server-sent completion chunks."""

        request_id, model, payload = self._generation_payload(request, stream=True)
        client = self._client_or_error()
        try:
            async with client.stream(
                "POST",
                self._config.chat_completions_path.lstrip("/"),
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError as error:
                        raise ProviderError(
                            ProviderErrorCategory.INVALID_RESPONSE,
                            self.name,
                        ) from error
                    if not isinstance(event, dict):
                        raise ProviderError(
                            ProviderErrorCategory.INVALID_RESPONSE,
                            self.name,
                        )
                    self._raise_embedded_error(event)
                    chunk = self._parse_chunk(event, request_id, model)
                    if chunk is not None:
                        yield chunk
        except httpx.TimeoutException as error:
            raise ProviderError(ProviderErrorCategory.TIMEOUT, self.name) from error
        except httpx.RequestError as error:
            raise ProviderError(ProviderErrorCategory.UNAVAILABLE, self.name) from error

    async def close(self) -> None:
        """Close the HTTP client idempotently."""

        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._client_or_error()
        try:
            response = await client.request(method, path.lstrip("/"), json=json_body)
        except httpx.TimeoutException as error:
            raise ProviderError(ProviderErrorCategory.TIMEOUT, self.name) from error
        except httpx.RequestError as error:
            raise ProviderError(ProviderErrorCategory.UNAVAILABLE, self.name) from error
        self._raise_for_status(response)
        try:
            payload = response.json()
        except ValueError as error:
            raise ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                self.name,
            ) from error
        if not isinstance(payload, dict):
            raise ProviderError(ProviderErrorCategory.INVALID_RESPONSE, self.name)
        return payload

    def _generation_payload(
        self,
        request: GenerationRequest,
        *,
        stream: bool,
    ) -> tuple[str, str, dict[str, Any]]:
        request_id = request.request_id or uuid4().hex
        model = request.model or self._config.default_model
        max_tokens = request.max_tokens or self._config.max_tokens
        temperature = (
            request.temperature if request.temperature is not None else self._config.temperature
        )
        if max_tokens > self._config.max_tokens:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, self.name)
        messages = [message.model_dump(mode="json") for message in request.messages]
        prompt_size = len(
            json.dumps(
                messages,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if prompt_size > self._config.max_prompt_bytes:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, self.name)
        return (
            request_id,
            model,
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
            },
        )

    def _parse_chunk(
        self,
        event: dict[str, Any],
        request_id: str,
        default_model: str,
    ) -> GenerationChunk | None:
        try:
            choices = event.get("choices")
            if not isinstance(choices, list) or not choices:
                return None
            choice = choices[0]
            if not isinstance(choice, dict):
                raise TypeError
            delta_object = choice.get("delta", {})
            if not isinstance(delta_object, dict):
                raise TypeError
            delta = delta_object.get("content") or ""
            finish_reason = choice.get("finish_reason")
            response_model = event.get("model", default_model)
            if not isinstance(delta, str) or not isinstance(response_model, str):
                raise TypeError
            if finish_reason is not None and not isinstance(finish_reason, str):
                raise TypeError
            return GenerationChunk(
                provider=self.name,
                request_id=request_id,
                model=response_model,
                delta=delta,
                finish_reason=finish_reason,
            )
        except (TypeError, ValidationError) as error:
            raise ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                self.name,
            ) from error

    def _parse_usage(self, value: object) -> TokenUsage:
        if value is None:
            return TokenUsage()
        if not isinstance(value, dict):
            raise TypeError
        input_tokens = self._non_negative_int(value.get("prompt_tokens", 0))
        output_tokens = self._non_negative_int(value.get("completion_tokens", 0))
        total_tokens = self._non_negative_int(
            value.get("total_tokens", input_tokens + output_tokens)
        )
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        if 200 <= response.status_code < 300:
            return
        retry_after: float | None = None
        retry_header = response.headers.get("Retry-After")
        if retry_header is not None:
            try:
                retry_after = max(float(retry_header), 0)
            except ValueError:
                retry_after = None
        raise ProviderError(
            self._category_for_status(response.status_code),
            self.name,
            retry_after_seconds=retry_after,
        )

    def _raise_embedded_error(self, payload: dict[str, Any]) -> None:
        error = payload.get("error")
        if not isinstance(error, dict):
            return
        code = error.get("code")
        category = (
            self._category_for_status(code)
            if isinstance(code, int)
            else ProviderErrorCategory.UNAVAILABLE
        )
        raise ProviderError(category, self.name)

    def _client_or_error(self) -> httpx.AsyncClient:
        if self._client is None:
            raise ProviderError(ProviderErrorCategory.UNAVAILABLE, self.name)
        return self._client

    @staticmethod
    def _category_for_status(status_code: int) -> ProviderErrorCategory:
        if status_code == 408:
            return ProviderErrorCategory.TIMEOUT
        if status_code in {401, 403}:
            return ProviderErrorCategory.AUTHENTICATION
        if status_code in {402, 429}:
            return ProviderErrorCategory.RATE_LIMIT
        if status_code >= 500:
            return ProviderErrorCategory.UNAVAILABLE
        return ProviderErrorCategory.INVALID_REQUEST

    @staticmethod
    def _non_negative_int(value: object) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TypeError
        return value

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)
