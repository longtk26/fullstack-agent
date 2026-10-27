"""Model prices (USD per 1M tokens) and per-call cost accounting (Story 8.4).

Claude Code reports the exact cost of a session per model; that cost is split over the session's calls by their
token weight, so the calls add up to what the CLI reported (`reported`). Antigravity reports no cost: each call is
tokens × price (`estimated`). A model without a price gets no cost, never a guess.
"""

from collections import defaultdict
from collections.abc import Mapping

from .port import ModelCall

Price = Mapping[str, float]  # input, output, cache_read, cache_write

DEFAULT_PRICES: dict[str, dict[str, float]] = {
    # Anthropic list prices. Claude Code writes 1-hour cache entries, which bill at 2x input.
    "claude-fable-5-1": {"input": 10.0, "output": 50.0, "cache_read": 0.25, "cache_write": 20.0},
    "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 8.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 4.0},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.20},
    # Gemini API list price (introductory, until 2026-12-31). agy model ids add an effort suffix (`-medium`).
    "gemini-3.8-flash": {"input": 0.75, "output": 3.75, "cache_read": 0.075},
}
# Only the ratios matter when a reported total is split over calls of a model without a price.
_RATIO_PRICE = {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 2.0}


def configured_prices() -> dict[str, Price]:
    """The defaults above, overridden per model by `MODEL_PRICES` (JSON)."""
    from src.configs import config

    return {**DEFAULT_PRICES, **config.model_prices}


def price_for(model: str | None, prices: Mapping[str, Price]) -> Price | None:
    """Exact id first, then the longest table key the id starts with (`gemini-3.8-flash-medium`)."""
    if not model:
        return None
    if model in prices:
        return prices[model]
    matches = [key for key in prices if model.startswith(key)]
    return prices[max(matches, key=len)] if matches else None


def call_cost(call: ModelCall, price: Price) -> float:
    uncached = max(0, call.input_tokens - call.cache_read_tokens - call.cache_write_tokens)
    return (
        uncached * price["input"]
        + call.cache_read_tokens * price.get("cache_read", price["input"])
        + call.cache_write_tokens * price.get("cache_write", price["input"])
        + call.output_tokens * price["output"]
    ) / 1_000_000


def estimate(calls: list[ModelCall], prices: Mapping[str, Price]) -> float | None:
    """Prices every call it can; returns the session total, or None when any call has no price."""
    total: float | None = 0.0
    for call in calls:
        price = price_for(call.model, prices)
        if price is None:
            call.cost_usd, call.cost_source = None, None
            total = None
            continue
        call.cost_usd, call.cost_source = round(call_cost(call, price), 6), "estimated"
        if total is not None:
            total += call.cost_usd
    return round(total, 6) if total is not None else None


def apportion(calls: list[ModelCall], reported: Mapping[str, Mapping[str, float]], prices: Mapping[str, Price]):
    """Splits each model's reported session cost over its calls (`reported` maps model → {cost, outputTokens}).

    Claude Code's per-message output counts are partial (they come from the start of the stream), so they are
    first scaled to the session's reported output for that model; input and cache counts are exact."""
    by_model: dict[str | None, list[ModelCall]] = defaultdict(list)
    for call in calls:
        by_model[_reported_key(call.model, reported)].append(call)
    for model, group in by_model.items():
        totals = reported.get(model or "")
        if totals is None:
            estimate(group, prices)
            continue
        _scale_output(group, int(totals.get("outputTokens") or 0))
        price = price_for(model, prices) or _RATIO_PRICE
        weights = [call_cost(call, price) for call in group]
        weight_sum = sum(weights)
        cost = float(totals.get("cost") or 0.0)
        for call, weight in zip(group, weights, strict=True):
            share = weight / weight_sum if weight_sum else 1 / len(group)
            call.cost_usd, call.cost_source = round(cost * share, 6), "reported"


def _reported_key(model: str | None, reported: Mapping[str, object]) -> str | None:
    """Messages name a dated id (`claude-haiku-4-5-20251001`), the session totals the alias."""
    if model is None or model in reported:
        return model
    return next((key for key in reported if model.startswith(key) or key.startswith(model)), model)


def _scale_output(group: list[ModelCall], reported_output: int) -> None:
    observed = sum(call.output_tokens for call in group)
    if not reported_output or observed == reported_output:
        return
    if not observed:
        for call in group:
            call.output_tokens = reported_output // len(group)
        group[-1].output_tokens += reported_output - sum(call.output_tokens for call in group)
        return
    for call in group:
        call.output_tokens = int(call.output_tokens * reported_output / observed)
    group[-1].output_tokens += reported_output - sum(call.output_tokens for call in group)
