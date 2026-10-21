"""LLM Analysis Tool backed by the existing Provider Router."""

import logging
from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.core.errors import RequestValidationError
from toolbridge.providers.application.budget_selection import estimate_tokens, select_budget_models
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import ChatMessage, GenerationRequest, ProviderStatus
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.llm_analysis import (
    AnalysisOperation,
    LLMAnalysisInput,
    LLMAnalysisOutput,
)
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus
from toolbridge.tools.domain.tool_errors import LLMAnalysisUnavailableError

_logger = logging.getLogger(__name__)


class LLMAnalysisTool(BaseTool):
    """Perform bounded analysis while hiding all provider-specific behavior."""

    def __init__(
        self,
        router: ProviderRouter,
        *,
        timeout_seconds: float,
        max_input_characters: int,
        max_tokens: int,
        temperature: float,
        model: str | None,
        system_prompt: str,
    ) -> None:
        self._router = router
        self._max_input_characters = max_input_characters
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._model = model
        self._system_prompt = system_prompt
        self._definition = ToolDefinition(
            name="llm_analysis",
            description=(
                "Analyze or summarize untrusted text through the configured LLM Provider Router."
            ),
            input_model=LLMAnalysisInput,
            output_model=LLMAnalysisOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable LLM Analysis registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Mark the router integration ready; the process owns router lifecycle."""

        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: LLMAnalysisInput) -> LLMAnalysisOutput:
        """Build a provider-neutral request and normalize the response."""

        if len(arguments.text) > self._max_input_characters:
            raise RequestValidationError(
                "The analysis text exceeds the configured limit.",
                details={"max_characters": self._max_input_characters},
            )
        operation_prompt = (
            "Analyze the document and identify its main themes, claims, and notable risks."
            if arguments.operation is AnalysisOperation.ANALYZE
            else "Summarize the document faithfully and concisely."
        )
        if arguments.instructions:
            operation_prompt = f"{operation_prompt}\nAdditional request: {arguments.instructions}"
        request = GenerationRequest(
            messages=(
                ChatMessage(role="system", content=self._system_prompt),
                ChatMessage(
                    role="user",
                    content=f"{operation_prompt}\n\n<document>\n{arguments.text}\n</document>",
                ),
            ),
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )
        selection_reason = "configured model" if self._model else "router ranking"
        try:
            response = None
            for choice in self._budget_choices(arguments):
                try:
                    response = await self._router.generate(
                        request.model_copy(update={"model": choice.model.id})
                    )
                except ProviderError:
                    continue
                selection_reason = f"auto low-budget: {choice.reason}"
                break
            if response is None:
                response = await self._router.generate(request)
        except ProviderError as error:
            self._last_failure_at = datetime.now(UTC)
            raise LLMAnalysisUnavailableError(error.category.value) from error
        _logger.info(
            "llm_analysis model selected",
            extra={
                "model": response.model,
                "provider": response.provider,
                "reason": selection_reason,
            },
        )
        self._last_success_at = datetime.now(UTC)
        return LLMAnalysisOutput(
            operation=arguments.operation,
            content=response.content,
            provider=response.provider,
            model=response.model,
            request_id=response.request_id,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
            model_selection_reason=selection_reason,
        )

    def _budget_choices(self, arguments: LLMAnalysisInput) -> tuple:
        """Auto mode (no fixed model): free first, then cheapest paid, task-aware."""

        if self._model is not None:
            return ()
        discovered = getattr(self._router, "discovered_models", None)
        if not callable(discovered):
            return ()
        try:
            models = tuple(discovered())
        except Exception:  # noqa: BLE001
            return ()
        priority = tuple(getattr(self._router, "priority", ()) or ())
        prompt = arguments.text + (arguments.instructions or "")
        return select_budget_models(
            models,
            provider=priority[0] if priority else None,
            operation=arguments.operation.value,
            prompt_tokens=estimate_tokens(prompt),
            max_output_tokens=self._max_tokens,
            complex_request=bool(arguments.instructions and len(arguments.instructions) > 200),
        )

    async def health_check(self) -> ToolHealthStatus:
        """Summarize current router state without issuing an LLM request."""

        state: ToolHealthState
        if self._state in {ToolHealthState.UNINITIALIZED, ToolHealthState.CLOSED}:
            state = self._state
            providers: dict[str, str] = {}
        else:
            snapshots = self._router.provider_status()
            # Plugin providers may report a plain string name instead of ProviderName.
            providers = {
                str(getattr(value.provider, "value", value.provider)): value.status.value
                for value in snapshots
            }
            available = sum(
                value.status not in {ProviderStatus.UNAVAILABLE, ProviderStatus.CLOSED}
                for value in snapshots
            )
            state = ToolHealthState.HEALTHY if available else ToolHealthState.UNAVAILABLE
        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
            providers=providers,
        )

    async def close(self) -> None:
        """Mark the integration closed without closing the process-owned router."""

        self._state = ToolHealthState.CLOSED
