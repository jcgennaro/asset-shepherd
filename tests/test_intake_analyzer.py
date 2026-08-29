"""Acceptance for provider-neutral semantic target intake."""

import json
import os

import httpx
import pytest

from asset_shepherd.intake_analyzer import (
    BEDROCK_INTAKE_TOOL,
    INTAKE_REFUSAL_MESSAGE,
    OPENAI_INTAKE_MODEL,
    BedrockTargetIntakeAnalyzer,
    BedrockTargetIntakeConfiguration,
    OpenAITargetIntakeAnalyzer,
    OpenAITargetIntakeConfiguration,
    TargetDimensionsInference,
    TargetIntakeAnalysisError,
    TargetIntakeContentRefusal,
    TargetIntakeInference,
    build_target_intake_analyzer,
    contract_from_inference,
    load_bedrock_target_intake_configuration,
)
from asset_shepherd.models import AssetEndpoint, AssetTargetUse
from asset_shepherd.target_intake import TargetEvidenceSource


def _response(inference: dict[str, object]) -> dict[str, object]:
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(inference)}],
            }
        ]
    }


def _tool_response(inference: dict[str, object]) -> dict[str, object]:
    return {
        "output": [
            {
                "type": "function_call",
                "name": BEDROCK_INTAKE_TOOL,
                "call_id": "call-1",
                "arguments": json.dumps(inference),
            }
        ]
    }


def test_openai_luna_xhigh_proposes_semantic_use_and_scale() -> None:
    """Ordinary language can yield a confirmable proposal without duplicate form questions."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json=_response(
                {
                    "engagement_decision": "PROCEED",
                    "asset_name": "Goop Mountain",
                    "target_use": "STATIC_GAME_ASSET",
                    "target_use_confidence": 0.96,
                    "target_use_evidence": "A mountain is an environmental game-world feature.",
                    "endpoint": "GODOT",
                    "endpoint_detail": None,
                    "endpoint_confidence": 0.9,
                    "endpoint_evidence": "The surreal game is being built in Godot.",
                    "target_dimensions_cm": {
                        "x_cm": 60000.0,
                        "y_cm": 80000.0,
                        "z_cm": 50000.0,
                    },
                    "target_dimensions_confidence": 0.91,
                    "target_dimensions_evidence": (
                        "A mountain requires a kilometer-scale vertical target."
                    ),
                    "expected_piece_count": 1,
                    "expected_piece_count_evidence": "The description identifies one mountain.",
                }
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    analyzer = OpenAITargetIntakeAnalyzer(
        OpenAITargetIntakeConfiguration(api_key="test-key"),
        client=client,
    )

    contract = analyzer.analyze("A mountain of goop for a surreal game world.")

    assert contract.ready_for_confirmation
    assert contract.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert contract.target_height_cm == 80000.0
    assert contract.target_dimensions_cm == (60000.0, 80000.0, 50000.0)
    assert contract.endpoint is AssetEndpoint.GODOT
    assert contract.analyzer_provider == "openai"
    assert contract.analyzer_model == OPENAI_INTAKE_MODEL
    assert contract.asset_name == "Goop Mountain"
    assert contract.expected_piece_count == 1
    assert contract.expected_piece_count_evidence == "The description identifies one mountain."
    assert {item.source for item in contract.evidence} == {TargetEvidenceSource.MODEL_INFERENCE}
    assert captured["model"] == OPENAI_INTAKE_MODEL
    assert captured["reasoning"] == {"effort": "xhigh"}
    assert captured["store"] is False
    text = captured["text"]
    assert isinstance(text, dict)
    assert text["format"]["strict"] is True
    assert "prefixItems" not in json.dumps(text["format"]["schema"])
    instructions = captured["instructions"]
    assert isinstance(instructions, str)
    assert "Usually this is 1" in instructions


def test_low_confidence_model_fields_become_questions() -> None:
    """Untrusted or genuinely ambiguous proposals do not cross the typed confidence gate."""
    contract = contract_from_inference(
        "An abstract shape that could play several unrelated roles in the game.",
        TargetIntakeInference(
            engagement_decision="PROCEED",
            asset_name="Abstract Shape",
            target_use=None,
            target_use_confidence=0.4,
            target_use_evidence=None,
            endpoint=None,
            endpoint_detail=None,
            endpoint_confidence=0.3,
            endpoint_evidence=None,
            target_dimensions_cm=None,
            target_dimensions_confidence=0.3,
            target_dimensions_evidence=None,
            expected_piece_count=1,
            expected_piece_count_evidence="The description identifies one abstract asset.",
        ),
        provider="openai",
        model_id=OPENAI_INTAKE_MODEL,
    )

    assert contract.missing_fields == ("target_use", "endpoint", "target_dimensions_cm")
    assert not contract.ready_for_confirmation

    with pytest.raises(ValueError, match="confidence gate"):
        TargetIntakeInference(
            engagement_decision="PROCEED",
            asset_name="Abstract Shape",
            target_use=None,
            target_use_confidence=0.9,
            target_use_evidence=None,
            endpoint=None,
            endpoint_detail=None,
            endpoint_confidence=0.3,
            endpoint_evidence=None,
            target_dimensions_cm=None,
            target_dimensions_confidence=0.3,
            target_dimensions_evidence=None,
            expected_piece_count=1,
            expected_piece_count_evidence="The description identifies one abstract asset.",
        )


def test_canonical_endpoint_discards_redundant_model_detail() -> None:
    """A correct canonical endpoint is not rejected because the model also names it in detail."""
    inference = TargetIntakeInference(
        engagement_decision="PROCEED",
        asset_name="Maintenance Robot",
        target_use=AssetTargetUse.PLAYABLE_CHARACTER,
        target_use_confidence=0.95,
        target_use_evidence="The robot has a walk cycle for player use.",
        endpoint=AssetEndpoint.UNITY,
        endpoint_detail="Unity third-person game",
        endpoint_confidence=0.98,
        endpoint_evidence="The user explicitly named Unity.",
        target_dimensions_cm=TargetDimensionsInference(x_cm=80.0, y_cm=180.0, z_cm=50.0),
        target_dimensions_confidence=0.99,
        target_dimensions_evidence="The user explicitly specified 1.8 m height.",
        expected_piece_count=1,
        expected_piece_count_evidence="The description identifies one robot.",
    )

    assert inference.endpoint is AssetEndpoint.UNITY
    assert inference.endpoint_detail is None


def test_unknown_endpoint_discards_explanatory_orphan_evidence() -> None:
    """An unknown engine becomes one missing-field question instead of a failed intake."""
    inference = TargetIntakeInference.model_validate_json(
        json.dumps(
            {
                "engagement_decision": "PROCEED",
                "asset_name": "Computer Chip",
                "target_use": "STATIC_GAME_ASSET",
                "target_use_confidence": 0.96,
                "target_use_evidence": "The chip is a static game prop.",
                "endpoint": None,
                "endpoint_detail": None,
                "endpoint_confidence": 0.3,
                "endpoint_evidence": "No destination engine was specified.",
                "target_dimensions_cm": {"x_cm": 5.0, "y_cm": 1.0, "z_cm": 5.0},
                "target_dimensions_confidence": 0.99,
                "target_dimensions_evidence": "The user supplied 5 by 5 by 1 cm bounds.",
                "expected_piece_count": 1,
                "expected_piece_count_evidence": "The description identifies one chip.",
            }
        )
    )

    contract = contract_from_inference(
        "A computer chip, around 5x5x1 cm.",
        inference,
        provider="openai",
        model_id=OPENAI_INTAKE_MODEL,
    )

    assert inference.endpoint is None
    assert inference.endpoint_evidence is None
    assert contract.missing_fields == ("endpoint",)
    assert contract.asset_name == "Computer Chip"
    assert contract.target_dimensions_cm == (5.0, 1.0, 5.0)


def test_disallowed_intake_returns_only_a_concise_refusal() -> None:
    """The model can refuse without creating target fields or improvising public copy."""
    assert "can't engage with this type of content" in INTAKE_REFUSAL_MESSAGE
    assert "work on something else" in INTAKE_REFUSAL_MESSAGE

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert INTAKE_REFUSAL_MESSAGE in payload["instructions"]
        return httpx.Response(
            200,
            json=_response(
                {
                    "engagement_decision": "REFUSE",
                    "asset_name": None,
                    "target_use": None,
                    "target_use_confidence": 0.0,
                    "target_use_evidence": None,
                    "endpoint": None,
                    "endpoint_detail": None,
                    "endpoint_confidence": 0.0,
                    "endpoint_evidence": None,
                    "target_dimensions_cm": None,
                    "target_dimensions_confidence": 0.0,
                    "target_dimensions_evidence": None,
                    "expected_piece_count": None,
                    "expected_piece_count_evidence": None,
                }
            ),
        )

    analyzer = OpenAITargetIntakeAnalyzer(
        OpenAITargetIntakeConfiguration(api_key="test-key"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TargetIntakeContentRefusal) as caught:
        analyzer.analyze("A sufficiently long description that the model declines.")
    assert str(caught.value) == INTAKE_REFUSAL_MESSAGE


def test_openai_failure_is_safe_and_does_not_expose_credentials() -> None:
    """Provider failures return a bounded public error without secret or body details."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "secret-provider-detail"}})

    analyzer = OpenAITargetIntakeAnalyzer(
        OpenAITargetIntakeConfiguration(api_key="never-print-this"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TargetIntakeAnalysisError) as caught:
        analyzer.analyze("A mountain of goop for a surreal game world.")
    message = str(caught.value)
    assert message == "The intake model is busy. Try again in a moment."
    assert "never-print-this" not in message
    assert "secret-provider-detail" not in message


def test_openai_bad_request_uses_plain_public_copy() -> None:
    """Schema/provider details stay in server diagnostics rather than the intake screen."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "unsupported schema keyword"}})

    analyzer = OpenAITargetIntakeAnalyzer(
        OpenAITargetIntakeConfiguration(api_key="test-key"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TargetIntakeAnalysisError) as caught:
        analyzer.analyze("A mountain of goop for a surreal game world.")
    assert str(caught.value) == "I couldn't analyze that description right now. Try again."


def test_provider_builder_requires_explicit_openai_configuration() -> None:
    """The network provider fails closed while offline intake stays credential-free."""
    with pytest.raises(TargetIntakeAnalysisError, match="OPENAI_API_KEY"):
        build_target_intake_analyzer({})

    offline = build_target_intake_analyzer({"ASSET_SHEPHERD_INTAKE_PROVIDER": "deterministic"})
    assert offline.provider == "deterministic"


def test_bedrock_intake_forces_one_validated_function_submission() -> None:
    """Bedrock intake retains Luna/xhigh semantics through a constrained client-side tool."""
    captured: dict[str, object] = {}
    credential_calls: list[str] = []

    def token_provider(region: str) -> str:
        credential_calls.append(region)
        return "short-term-test-token"

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.url == (
            "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1/responses"
        )
        assert request.headers["authorization"] == "Bearer short-term-test-token"
        return httpx.Response(
            200,
            json=_tool_response(
                {
                    "engagement_decision": "PROCEED",
                    "asset_name": "Computer Chip",
                    "target_use": "STATIC_GAME_ASSET",
                    "target_use_confidence": 0.98,
                    "target_use_evidence": "The chip is a handheld static game prop.",
                    "endpoint": "UNREAL",
                    "endpoint_detail": None,
                    "endpoint_confidence": 0.99,
                    "endpoint_evidence": "The description explicitly names Unreal.",
                    "target_dimensions_cm": {
                        "x_cm": 7.0,
                        "y_cm": 1.2,
                        "z_cm": 6.23,
                    },
                    "target_dimensions_confidence": 0.99,
                    "target_dimensions_evidence": "The description supplies approximate bounds.",
                    "expected_piece_count": 1,
                    "expected_piece_count_evidence": "The description identifies one chip.",
                }
            ),
        )

    configuration = BedrockTargetIntakeConfiguration(
        model_id="us.openai.gpt-5.6-luna",
        region="us-east-1",
        token_provider=token_provider,
    )
    analyzer = BedrockTargetIntakeAnalyzer(
        configuration,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    contract = analyzer.analyze("One computer chip for Unreal, approximately 7 x 1.2 x 6.23 cm.")

    assert credential_calls == ["us-east-1"]
    assert contract.analyzer_provider == "bedrock"
    assert contract.analyzer_model == "us.openai.gpt-5.6-luna"
    assert contract.target_dimensions_cm == (7.0, 1.2, 6.23)
    assert captured["model"] == "us.openai.gpt-5.6-luna"
    assert captured["reasoning"] == {"effort": "xhigh"}
    assert captured["parallel_tool_calls"] is False
    assert captured["store"] is False
    assert captured["tool_choice"] == {"type": "function", "name": BEDROCK_INTAKE_TOOL}
    text = captured["text"]
    assert isinstance(text, dict)
    assert "format" not in text
    tools = captured["tools"]
    assert isinstance(tools, list)
    assert tools[0]["name"] == BEDROCK_INTAKE_TOOL
    assert tools[0]["strict"] is True


@pytest.mark.parametrize(
    "output",
    [
        [],
        [{"type": "function_call", "name": "wrong_tool", "arguments": "{}"}],
        [
            {"type": "function_call", "name": BEDROCK_INTAKE_TOOL, "arguments": "{}"},
            {"type": "function_call", "name": BEDROCK_INTAKE_TOOL, "arguments": "{}"},
        ],
    ],
)
def test_bedrock_intake_rejects_absent_wrong_or_repeated_submissions(
    output: list[dict[str, object]],
) -> None:
    """The constrained intake boundary fails closed if its one-call invariant is violated."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": output})

    analyzer = BedrockTargetIntakeAnalyzer(
        BedrockTargetIntakeConfiguration(
            model_id="us.openai.gpt-5.6-luna",
            region="us-east-1",
            token_provider=lambda _region: "test-token",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TargetIntakeAnalysisError, match="target submission"):
        analyzer.analyze("One computer chip for Unreal, approximately 7 x 1.2 x 6.23 cm.")


def test_bedrock_configuration_is_explicit_and_uses_runtime_endpoint() -> None:
    """Provider selection requires a regional inference profile and never an OpenAI key."""
    values = {
        "ASSET_SHEPHERD_INTAKE_PROVIDER": "bedrock",
        "ASSET_SHEPHERD_MODEL_ID": "us.openai.gpt-5.6-luna",
        "ASSET_SHEPHERD_AWS_REGION": "us-east-1",
        "ASSET_SHEPHERD_INTAKE_REASONING": "xhigh",
    }
    configuration = load_bedrock_target_intake_configuration(values)
    analyzer = build_target_intake_analyzer(values)

    assert configuration.responses_url == (
        "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1/responses"
    )
    assert analyzer.provider == "bedrock"
    assert "OPENAI_API_KEY" not in values

    with pytest.raises(TargetIntakeAnalysisError, match="inference profile"):
        load_bedrock_target_intake_configuration(
            {
                "ASSET_SHEPHERD_MODEL_ID": "openai.gpt-5.6-luna",
                "ASSET_SHEPHERD_AWS_REGION": "us-east-1",
            }
        )


def test_bedrock_authentication_failure_never_exposes_provider_detail() -> None:
    """IAM token failures stop before HTTP and expose only bounded intake copy."""

    def fail_token(_region: str) -> str:
        raise RuntimeError("sensitive credential-chain detail")

    analyzer = BedrockTargetIntakeAnalyzer(
        BedrockTargetIntakeConfiguration(
            model_id="us.openai.gpt-5.6-luna",
            region="us-east-1",
            token_provider=fail_token,
        )
    )

    with pytest.raises(TargetIntakeAnalysisError) as caught:
        analyzer.analyze("One computer chip for Unreal, approximately 7 x 1.2 x 6.23 cm.")
    assert str(caught.value) == "Amazon Bedrock authentication failed for intake."
    assert "sensitive" not in str(caught.value)


def test_bedrock_access_denial_has_actionable_bounded_copy() -> None:
    """An AWS verification/IAM hold is distinguishable without echoing its response body."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "private provider detail"}})

    analyzer = BedrockTargetIntakeAnalyzer(
        BedrockTargetIntakeConfiguration(
            model_id="us.openai.gpt-5.6-luna",
            region="us-east-1",
            token_provider=lambda _region: "test-token",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TargetIntakeAnalysisError) as caught:
        analyzer.analyze("One computer chip for Unreal, approximately 7 x 1.2 x 6.23 cm.")
    assert str(caught.value) == (
        "Amazon Bedrock access is not ready. Check account verification and runtime permissions."
    )
    assert "private provider detail" not in str(caught.value)


@pytest.mark.live
def test_opt_in_live_bedrock_target_intake() -> None:
    """Exercise the constrained intake submission through configured Bedrock when opted in."""
    if os.environ.get("ASSET_SHEPHERD_RUN_LIVE") != "1":
        pytest.skip("set ASSET_SHEPHERD_RUN_LIVE=1 with Bedrock configuration to opt in")
    analyzer = build_target_intake_analyzer()

    contract = analyzer.analyze(
        "One computer chip for an Unreal game, approximately 7 x 1.2 x 6.23 cm."
    )

    assert contract.analyzer_provider == "bedrock"
    assert contract.ready_for_confirmation
    assert contract.endpoint is AssetEndpoint.UNREAL
    assert contract.expected_piece_count == 1
