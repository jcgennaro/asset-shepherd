"""Unit tests for immutable Bedrock Guardrail configuration."""

import pytest

from asset_shepherd.bedrock_guardrail import load_optional_bedrock_guardrail


def test_optional_guardrail_is_absent_or_a_complete_immutable_pair() -> None:
    """Unconfigured local providers remain valid while deployed Bedrock uses a fixed version."""
    assert load_optional_bedrock_guardrail({}) is None

    configuration = load_optional_bedrock_guardrail(
        {
            "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_ID": "xadkxnj292qu",
            "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_VERSION": "1",
        }
    )

    assert configuration is not None
    assert configuration.identifier == "xadkxnj292qu"
    assert configuration.version == "1"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {"ASSET_SHEPHERD_BEDROCK_GUARDRAIL_ID": "xadkxnj292qu"},
            "must be configured together",
        ),
        (
            {
                "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_ID": "INVALID!",
                "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_VERSION": "1",
            },
            "ID is invalid",
        ),
        (
            {
                "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_ID": "xadkxnj292qu",
                "ASSET_SHEPHERD_BEDROCK_GUARDRAIL_VERSION": "DRAFT",
            },
            "immutable numeric version",
        ),
    ],
)
def test_optional_guardrail_rejects_ambiguous_or_mutable_configuration(
    values: dict[str, str], message: str
) -> None:
    """A partial, malformed, or draft Guardrail cannot silently weaken deployment."""
    with pytest.raises(ValueError, match=message):
        load_optional_bedrock_guardrail(values)
