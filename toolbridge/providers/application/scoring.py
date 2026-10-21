"""Capability-aware provider model scoring."""

from dataclasses import dataclass

from toolbridge.providers.domain.models import (
    GenerationRequest,
    ProviderCapability,
    ProviderModel,
    RoutingTask,
)

_TASK_CAPABILITIES = {
    RoutingTask.CHAT: ProviderCapability.CHAT,
    RoutingTask.REASONING: ProviderCapability.REASONING,
    RoutingTask.SUMMARIZATION: ProviderCapability.CHAT,
    RoutingTask.CODE: ProviderCapability.CODE_GENERATION,
    RoutingTask.VISION: ProviderCapability.VISION,
    RoutingTask.EMBEDDING: ProviderCapability.EMBEDDINGS,
    RoutingTask.IMAGE: ProviderCapability.IMAGE_GENERATION,
    RoutingTask.AUDIO: ProviderCapability.AUDIO_GENERATION,
    RoutingTask.WEB_SEARCH: ProviderCapability.WEB_SEARCH,
}


@dataclass(frozen=True, slots=True)
class RankedModel:
    """Internal score and explanation for one eligible model."""

    model: ProviderModel
    score: float
    reason: str


class ModelRankingEngine:
    """Rank available models by capability, health, latency, cost, and quality."""

    def rank(
        self,
        models: tuple[ProviderModel, ...],
        request: GenerationRequest,
        *,
        provider_health: dict[str, float],
        soft_limited: frozenset[str],
        explicit_priority: tuple[str, ...],
    ) -> tuple[RankedModel, ...]:
        """Return eligible models ordered best-first with deterministic ties."""

        required = set(request.required_capabilities)
        required.add(_TASK_CAPABILITIES[request.task])
        priority_index = {name: index for index, name in enumerate(explicit_priority)}
        ranked: list[RankedModel] = []
        for model in models:
            if not model.available or not model.capabilities.supports(frozenset(required)):
                continue
            if request.model is not None and model.id != request.model:
                continue
            health = provider_health.get(model.provider, model.health_score)
            latency = model.latency_ms or 0.0
            latency_score = max(0.0, 1.0 - min(latency, 10_000.0) / 10_000.0)
            cost = (
                model.input_cost_per_million_tokens_usd + model.output_cost_per_million_tokens_usd
            )
            cost_score = 1.0 if model.is_free else 1.0 / (1.0 + cost)
            score = health * 40 + latency_score * 15 + cost_score * 15
            score += model.reasoning_quality * 20
            score += 5 if model.is_free else 0
            score += 5 if model.context_window and model.context_window >= 100_000 else 0
            if model.provider in soft_limited:
                score -= 30
            if explicit_priority and model.provider in priority_index:
                score += max(0, len(explicit_priority) - priority_index[model.provider]) * 100
            reason = (
                f"capabilities matched; health={health:.2f}; "
                f"latency={latency:.1f}ms; {'free' if model.is_free else 'paid'}"
            )
            ranked.append(RankedModel(model=model, score=round(score, 3), reason=reason))
        return tuple(
            sorted(ranked, key=lambda item: (-item.score, item.model.provider, item.model.id))
        )
