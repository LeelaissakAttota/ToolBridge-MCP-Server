"""HCL Curie / LLM Analysis Tool backed by the existing Provider Router."""

from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.core.errors import RequestValidationError
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
            name="hcl_curie_analysis",
            description=(
                "Analyze or summarize untrusted text through the configured LLM "
                "Provider Router."
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
        try:
            response = await self._router.generate(request)
        except ProviderError as error:
            self._last_failure_at = datetime.now(UTC)
            raise LLMAnalysisUnavailableError(error.category.value) from error
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
        )

    async def health_check(self) -> ToolHealthStatus:
        """Summarize current router state without issuing an LLM request."""

        if self._state in {ToolHealthState.UNINITIALIZED, ToolHealthState.CLOSED}:
            state = self._state
            providers: dict[str, str] = {}
        else:
            snapshots = self._router.provider_status()
            providers = {value.provider.value: value.status.value for value in snapshots}
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
