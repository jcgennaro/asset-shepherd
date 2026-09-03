"""Fail-closed capability contract for Meta Model API evaluation."""

from __future__ import annotations

from typing import Literal, cast

META_MODEL_API_BASE_URL = "https://api.meta.ai/v1"
MUSE_SPARK_1_3_MODEL_ID = "muse-spark-1.3"
MUSE_SPARK_1_3_CONTRIBUTOR_MODEL_ID = "muse-spark-1.3-contributor"

MetaReasoningEffort = Literal["minimal", "low", "medium", "high"]


def validate_meta_model_id(model_id: str, *, allow_contributor: bool = False) -> str:
    """Allow the contributor checkpoint only behind explicit per-process data consent."""
    if model_id == MUSE_SPARK_1_3_MODEL_ID:
        return model_id
    if model_id == MUSE_SPARK_1_3_CONTRIBUTOR_MODEL_ID:
        if allow_contributor:
            return model_id
        raise ValueError("Muse contributor mode requires ASSET_SHEPHERD_ALLOW_META_TRAINING=1.")
    raise ValueError("Unsupported Meta Model API model. Choose a reviewed Muse Spark 1.3 model.")


def resolve_meta_reasoning_effort(value: str | None) -> MetaReasoningEffort:
    """Normalize Meta's xhigh alias to its documented effective maximum."""
    effort = value or "high"
    if effort == "xhigh":
        effort = "high"
    if effort not in {"minimal", "low", "medium", "high"}:
        raise ValueError("Muse Spark 1.3 reasoning effort must be minimal, low, medium, or high.")
    return cast(MetaReasoningEffort, effort)
