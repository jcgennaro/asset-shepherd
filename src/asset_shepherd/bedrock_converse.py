"""Capability registry for the model-neutral Amazon Bedrock Converse adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

BedrockConverseReasoning = Literal["low", "medium"]


@dataclass(frozen=True)
class BedrockConverseModel:
    """One explicitly tested model contract behind the shared Converse transport."""

    key: str
    display_name: str
    model_id: str
    workflow_max_tokens: int
    hint: str
    recommended: bool = False
    intake_max_tokens: int = 4096
    default_reasoning_effort: BedrockConverseReasoning | None = None
    reasoning_efforts: frozenset[BedrockConverseReasoning] = frozenset()
    requires_tool_result_image_hoisting: bool = False

    @property
    def supports_reasoning_configuration(self) -> bool:
        """Return whether this model accepts Asset Shepherd's Converse reasoning field."""
        return bool(self.reasoning_efforts)


_NOVA_PROFILE_PATTERN = re.compile(r"^(?:us|global)\.amazon\.nova-2-lite-v1:0$")

KIMI_K2_5 = BedrockConverseModel(
    key="kimi-k2.5",
    display_name="Kimi K2.5",
    model_id="moonshotai.kimi-k2.5",
    workflow_max_tokens=16_384,
    hint="Balanced visual reasoning and long repair turns.",
    recommended=True,
    requires_tool_result_image_hoisting=True,
)

CLAUDE_HAIKU_4_5 = BedrockConverseModel(
    key="claude-haiku-4.5",
    display_name="Claude Haiku 4.5",
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    workflow_max_tokens=16_384,
    hint="Experimental — fast; compare repair quality and cost before choosing it routinely.",
)

MISTRAL_LARGE_3 = BedrockConverseModel(
    key="mistral-large-3",
    display_name="Mistral Large 3",
    model_id="mistral.mistral-large-3-675b-instruct",
    workflow_max_tokens=16_384,
    hint="Experimental — try for especially long or complex repair conversations.",
    requires_tool_result_image_hoisting=True,
)

QWEN3_VL_235B = BedrockConverseModel(
    key="qwen3-vl-235b",
    display_name="Qwen3 VL 235B",
    model_id="qwen.qwen3-vl-235b-a22b",
    workflow_max_tokens=8192,
    hint="Experimental — try when visual evidence is the main uncertainty.",
    requires_tool_result_image_hoisting=True,
)

NOVA_2_LITE = BedrockConverseModel(
    key="nova-2-lite",
    display_name="Nova 2 Lite",
    model_id="us.amazon.nova-2-lite-v1:0",
    workflow_max_tokens=8192,
    hint="Lower-cost diagnostic — expect more user correction.",
    default_reasoning_effort="medium",
    reasoning_efforts=frozenset({"low", "medium"}),
)

_IN_REGION_MODELS = {
    model.model_id: model
    for model in (
        KIMI_K2_5,
        CLAUDE_HAIKU_4_5,
        MISTRAL_LARGE_3,
        QWEN3_VL_235B,
    )
}


def supported_bedrock_converse_models() -> tuple[BedrockConverseModel, ...]:
    """Return stable model choices suitable for a future workspace selector."""
    return (*_IN_REGION_MODELS.values(), NOVA_2_LITE)


def resolve_bedrock_converse_model(model_id: str) -> BedrockConverseModel:
    """Resolve an explicit model ID to its fail-closed Converse capability contract."""
    resolved = _IN_REGION_MODELS.get(model_id)
    if resolved is not None:
        return resolved
    if _NOVA_PROFILE_PATTERN.fullmatch(model_id):
        return BedrockConverseModel(
            key="nova-2-lite",
            display_name="Nova 2 Lite",
            model_id=model_id,
            workflow_max_tokens=8192,
            hint=NOVA_2_LITE.hint,
            default_reasoning_effort="medium",
            reasoning_efforts=frozenset({"low", "medium"}),
        )
    raise ValueError(
        "Unsupported Amazon Bedrock Converse model. Choose a registered model capability."
    )


def resolve_bedrock_converse_reasoning(
    model: BedrockConverseModel,
    configured_effort: str | None,
) -> BedrockConverseReasoning | None:
    """Validate an optional reasoning control without translating between providers."""
    if model.supports_reasoning_configuration:
        effort = configured_effort or model.default_reasoning_effort
        if effort not in model.reasoning_efforts:
            allowed = ", ".join(sorted(model.reasoning_efforts))
            raise ValueError(f"{model.display_name} reasoning effort must be one of: {allowed}.")
        return effort
    if configured_effort not in {None, "", "default", "none"}:
        raise ValueError(
            f"{model.display_name} does not expose configurable reasoning through Converse."
        )
    return None


def bedrock_converse_reasoning_fields(
    model: BedrockConverseModel,
    effort: BedrockConverseReasoning | None,
) -> dict[str, object]:
    """Return only the provider field proven for the selected model capability."""
    if model.key == "nova-2-lite" and effort is not None:
        return {
            "reasoningConfig": {
                "type": "enabled",
                "maxReasoningEffort": effort,
            }
        }
    return {}
