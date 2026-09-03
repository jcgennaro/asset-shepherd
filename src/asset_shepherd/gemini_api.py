"""Fail-closed configuration for the opt-in Google Gemini comparator."""

from typing import Literal, cast

GEMINI_3_8_FLASH_MODEL_ID = "gemini-3.8-flash"

GeminiReasoningEffort = Literal["low", "medium", "high"]


def validate_gemini_model_id(model_id: str) -> str:
    """Accept only the checkpoint covered by Asset Shepherd's evaluation contract."""
    if model_id != GEMINI_3_8_FLASH_MODEL_ID:
        raise ValueError("Gemini evaluation currently allows only gemini-3.8-flash.")
    return model_id


def resolve_gemini_reasoning_effort(value: str | None) -> GeminiReasoningEffort:
    """Use a bounded default while retaining an explicit xhigh-to-high mapping."""
    normalized = (value or "medium").lower()
    if normalized == "xhigh":
        normalized = "high"
    if normalized not in {"low", "medium", "high"}:
        raise ValueError("Gemini reasoning must be low, medium, high, or xhigh (high alias).")
    return cast(GeminiReasoningEffort, normalized)
