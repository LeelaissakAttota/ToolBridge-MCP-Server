"""Provider-aware base tool for tools that need LLM provider access."""

from __future__ import annotations

from typing import Any
from mcp_server.tools.base import BaseTool, ToolMetadata
from mcp_server.providers import (
    ProviderFactory,
    GenerationRequest,
    model_router,
    RoutingStrategy,
)


class ProviderAwareTool(BaseTool):
    """Base class for tools that require LLM provider access.

    Provides:
    - Automatic provider resolution via ModelRouter
    - Generation request helpers
    - Token/cost tracking
    - Provider health awareness
    """

    # Abstract base class attributes - must be overridden by concrete subclasses
    name = "provider_aware_base"
    description = "Abstract base class for provider-aware tools"

    # Override in subclasses
    DEFAULT_STRATEGY = RoutingStrategy.DEFAULT
    REQUIRES_PROVIDER = True

    def __init__(self, provider_factory: ProviderFactory | None = None, **kwargs):
        """Initialize provider-aware tool.

        Args:
            provider_factory: Provider factory instance (uses global if not provided)
            **kwargs: Additional arguments passed to BaseTool
        """
        super().__init__(**kwargs)
        self._provider_factory = provider_factory or model_router._factory
        self._total_tokens = 0
        self._total_cost = 0.0

    def _create_generation_request(
        self,
        prompt: str,
        model: str | None = None,
        strategy: RoutingStrategy | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        stream: bool = False,
        **extra_params,
    ) -> GenerationRequest:
        """Create a generation request with tool-specific defaults.

        Args:
            prompt: The prompt to send to the LLM
            model: Optional specific model override
            strategy: Routing strategy (defaults to tool's DEFAULT_STRATEGY)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
            **extra_params: Additional parameters for the provider

        Returns:
            GenerationRequest configured for the provider
        """
        return GenerationRequest(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            routing_strategy=strategy or self.DEFAULT_STRATEGY,
            extra_params=extra_params,
        )

    async def _generate(
        self,
        request: GenerationRequest,
        provider_name: str | None = None,
    ) -> Any:
        """Execute generation via ModelRouter with automatic failover.

        Args:
            request: Generation request
            provider_name: Optional explicit provider override

        Returns:
            GenerationResponse with text, tokens, cost, metadata
        """
        response = await model_router.generate(request, provider_name=provider_name)

        # Track tokens and cost
        self._total_tokens += response.total_tokens
        self._total_cost += response.cost_estimate

        return response

    async def _stream_generate(
        self,
        request: GenerationRequest,
        provider_name: str | None = None,
    ):
        """Stream generation via ModelRouter.

        Args:
            request: Generation request
            provider_name: Optional explicit provider override

        Yields:
            Text chunks as they are generated
        """
        async for chunk in model_router.stream(request, provider_name=provider_name):
            yield chunk

    def get_token_usage(self) -> dict[str, Any]:
        """Get cumulative token usage for this tool instance.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens, cost
        """
        return {
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
        }

    def reset_token_usage(self) -> None:
        """Reset token usage counters."""
        self._total_tokens = 0
        self._total_cost = 0.0

    async def check_provider_health(self, provider_name: str) -> bool:
        """Check if a specific provider is healthy.

        Args:
            provider_name: Name of provider to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            provider = self._provider_factory.get_instance(provider_name)
            if provider:
                health = await provider.health_check()
                return health.healthy
        except Exception:
            pass
        return False

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names.

        Returns:
            List of registered provider names
        """
        return self._provider_factory.list_instances()

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata including provider requirements."""
        metadata = super().get_metadata()
        # Add provider-specific metadata
        metadata.annotations = metadata.annotations or {}
        metadata.annotations["requires_provider"] = self.REQUIRES_PROVIDER
        metadata.annotations["default_strategy"] = self.DEFAULT_STRATEGY.value
        return metadata


class TextGenerationTool(ProviderAwareTool):
    """Tool for general-purpose text generation via LLM providers."""

    name = "text_generate"
    description = "Generate text using an LLM provider with automatic routing and failover"
    version = "1.0.0"
    DEFAULT_STRATEGY = RoutingStrategy.SMART

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to generate text from",
                },
                "model": {
                    "type": "string",
                    "description": "Optional specific model to use (overrides routing)",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["default", "fast", "smart", "fallback", "cost_optimized", "auto"],
                    "description": "Routing strategy for provider selection",
                    "default": "smart",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8192,
                    "description": "Maximum tokens to generate",
                    "default": 1000,
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "description": "Sampling temperature",
                    "default": 0.7,
                },
                "stream": {
                    "type": "boolean",
                    "description": "Whether to stream the response",
                    "default": False,
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Generated text"},
                "model": {"type": "string", "description": "Model used"},
                "provider": {"type": "string", "description": "Provider used"},
                "tokens": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "integer"},
                        "completion": {"type": "integer"},
                        "total": {"type": "integer"},
                    },
                },
                "cost_usd": {"type": "number", "description": "Estimated cost in USD"},
                "latency_ms": {"type": "number", "description": "Generation latency in milliseconds"},
                "finish_reason": {"type": "string", "description": "Why generation stopped"},
            },
            "required": ["text", "model", "provider", "tokens", "cost_usd", "latency_ms", "finish_reason"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute text generation."""
        prompt = arguments["prompt"]
        strategy_str = arguments.get("strategy", "smart")
        strategy = RoutingStrategy(strategy_str) if isinstance(strategy_str, str) else strategy_str

        request = self._create_generation_request(
            prompt=prompt,
            model=arguments.get("model"),
            strategy=strategy,
            max_tokens=arguments.get("max_tokens", 1000),
            temperature=arguments.get("temperature", 0.7),
            stream=arguments.get("stream", False),
        )

        response = await self._generate(request)

        return {
            "text": response.text,
            "model": response.model,
            "provider": response.provider,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens,
            },
            "cost_usd": response.cost_estimate,
            "latency_ms": response.latency_ms,
            "finish_reason": response.finish_reason,
        }


class CodeGenerationTool(ProviderAwareTool):
    """Tool for code generation via LLM providers."""

    name = "code_generate"
    description = "Generate code in any programming language using LLM providers"
    version = "1.0.0"
    DEFAULT_STRATEGY = RoutingStrategy.SMART

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Description of the code to generate",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, go, rust, etc.)",
                    "default": "python",
                },
                "model": {
                    "type": "string",
                    "description": "Optional specific model to use",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["default", "fast", "smart", "fallback", "cost_optimized", "auto"],
                    "description": "Routing strategy",
                    "default": "smart",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8192,
                    "default": 2000,
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.3,
                    "description": "Lower temperature for more deterministic code",
                },
                "include_tests": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include unit tests",
                },
                "include_docs": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include docstrings/comments",
                },
            },
            "required": ["task"],
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Generated code"},
                "language": {"type": "string", "description": "Programming language"},
                "model": {"type": "string"},
                "provider": {"type": "string"},
                "tokens": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "integer"},
                        "completion": {"type": "integer"},
                        "total": {"type": "integer"},
                    },
                },
                "cost_usd": {"type": "number"},
                "latency_ms": {"type": "number"},
            },
            "required": ["code", "language", "model", "provider", "tokens", "cost_usd", "latency_ms"],
        }

    def _build_code_prompt(self, arguments: dict[str, Any]) -> str:
        """Build a structured prompt for code generation."""
        task = arguments["task"]
        language = arguments.get("language", "python")
        include_tests = arguments.get("include_tests", False)
        include_docs = arguments.get("include_docs", True)

        parts = [
            f"Generate {language} code for the following task:",
            f"\nTask: {task}\n",
            "Requirements:",
            f"- Write clean, idiomatic {language} code",
            "- Follow best practices and conventions",
        ]

        if include_docs:
            parts.append("- Include comprehensive docstrings/comments")

        if include_tests:
            parts.append("- Include unit tests using standard testing framework")

        parts.append("\nOutput ONLY the code, no explanations or markdown formatting.")

        return "\n".join(parts)

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute code generation."""
        prompt = self._build_code_prompt(arguments)
        strategy_str = arguments.get("strategy", "smart")
        strategy = RoutingStrategy(strategy_str) if isinstance(strategy_str, str) else strategy_str

        request = self._create_generation_request(
            prompt=prompt,
            model=arguments.get("model"),
            strategy=strategy,
            max_tokens=arguments.get("max_tokens", 2000),
            temperature=arguments.get("temperature", 0.3),
        )

        response = await self._generate(request)

        return {
            "code": response.text.strip(),
            "language": arguments.get("language", "python"),
            "model": response.model,
            "provider": response.provider,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens,
            },
            "cost_usd": response.cost_estimate,
            "latency_ms": response.latency_ms,
        }


class TextAnalysisTool(ProviderAwareTool):
    """Tool for text analysis tasks (summarization, sentiment, extraction, etc.)."""

    name = "text_analyze"
    description = "Analyze text: summarize, extract entities, sentiment, key points, classify"
    version = "1.0.0"
    DEFAULT_STRATEGY = RoutingStrategy.SMART

    ANALYSIS_TYPES = [
        "summarize",
        "sentiment",
        "entities",
        "key_points",
        "classify",
        "extract_structured",
        "translate",
        "simplify",
    ]

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": self.ANALYSIS_TYPES,
                    "description": "Type of analysis to perform",
                },
                "model": {
                    "type": "string",
                    "description": "Optional specific model to use",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["default", "fast", "smart", "fallback", "cost_optimized", "auto"],
                    "default": "smart",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4096,
                    "default": 1000,
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.3,
                    "description": "Lower temperature for analytical tasks",
                },
                "language": {
                    "type": "string",
                    "description": "Target language for translation",
                    "default": "english",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON schema for structured extraction",
                },
            },
            "required": ["text", "analysis_type"],
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Analysis result"},
                "analysis_type": {"type": "string"},
                "model": {"type": "string"},
                "provider": {"type": "string"},
                "tokens": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "integer"},
                        "completion": {"type": "integer"},
                        "total": {"type": "integer"},
                    },
                },
                "cost_usd": {"type": "number"},
                "latency_ms": {"type": "number"},
            },
            "required": ["result", "analysis_type", "model", "provider", "tokens", "cost_usd", "latency_ms"],
        }

    def _build_analysis_prompt(self, arguments: dict[str, Any]) -> str:
        """Build analysis-specific prompt."""
        text = arguments["text"]
        analysis_type = arguments["analysis_type"]
        language = arguments.get("language", "english")
        schema = arguments.get("schema")

        prompts = {
            "summarize": f"Summarize the following text concisely in {language}:\n\n{text}",
            "sentiment": f"Analyze the sentiment of the following text. Return only: positive, negative, or neutral with a brief explanation:\n\n{text}",
            "entities": f"Extract all named entities (people, organizations, locations, dates, etc.) from the following text. Format as a list:\n\n{text}",
            "key_points": f"Extract the key points from the following text as a bullet list:\n\n{text}",
            "classify": f"Classify the following text into a single category (e.g., news, technical, marketing, legal, academic, personal, etc.):\n\n{text}",
            "extract_structured": f"Extract structured data from the following text according to the provided schema. Return valid JSON only:\n\nText: {text}\n\nSchema: {schema}",
            "translate": f"Translate the following text to {language}:\n\n{text}",
            "simplify": f"Rewrite the following text in simpler terms while preserving the meaning:\n\n{text}",
        }

        return prompts.get(analysis_type, f"Analyze: {text}")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute text analysis."""
        prompt = self._build_analysis_prompt(arguments)
        strategy_str = arguments.get("strategy", "smart")
        strategy = RoutingStrategy(strategy_str) if isinstance(strategy_str, str) else strategy_str

        request = self._create_generation_request(
            prompt=prompt,
            model=arguments.get("model"),
            strategy=strategy,
            max_tokens=arguments.get("max_tokens", 1000),
            temperature=arguments.get("temperature", 0.3),
        )

        response = await self._generate(request)

        return {
            "result": response.text.strip(),
            "analysis_type": arguments["analysis_type"],
            "model": response.model,
            "provider": response.provider,
            "tokens": {
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens,
            },
            "cost_usd": response.cost_estimate,
            "latency_ms": response.latency_ms,
        }