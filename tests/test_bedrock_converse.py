"""Capability-contract tests for Asset Shepherd's Bedrock Converse allowlist."""

import pytest

from asset_shepherd.bedrock_converse import (
    KIMI_K2_5,
    NOVA_2_LITE,
    resolve_bedrock_converse_model,
    supported_bedrock_converse_models,
)


def test_model_allowlist_has_one_recommended_choice_and_actionable_hints() -> None:
    """The UI allowlist stays small, explicit, and useful to a non-expert."""
    models = supported_bedrock_converse_models()

    assert [model.display_name for model in models] == [
        "Kimi K2.5",
        "Mistral Large 3",
        "Qwen3 VL 235B",
        "Nova 2 Lite",
    ]
    assert [model for model in models if model.recommended] == [KIMI_K2_5]
    assert len({model.model_id for model in models}) == len(models)
    assert all(model.hint.endswith(".") for model in models)


def test_model_resolution_is_fail_closed_but_accepts_supported_nova_profiles() -> None:
    """Arbitrary model IDs cannot bypass the adapter's tested capability contracts."""
    assert resolve_bedrock_converse_model(KIMI_K2_5.model_id) is KIMI_K2_5
    assert resolve_bedrock_converse_model(NOVA_2_LITE.model_id).key == "nova-2-lite"
    assert resolve_bedrock_converse_model("global.amazon.nova-2-lite-v1:0").model_id.startswith(
        "global."
    )

    with pytest.raises(ValueError, match="registered model capability"):
        resolve_bedrock_converse_model("some-provider.unreviewed-model")
