"""No-network checks for explicit hosted providers and backend-only credentials."""

from asyncio import run
from dataclasses import asdict
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from asset_shepherd import hosted_models
from asset_shepherd.agent_job import AgentWorkflowError
from asset_shepherd.agent_runtime import CompleteResponseOpenAIModel
from asset_shepherd.agentcore_runtime import _model_values  # pyright: ignore[reportPrivateUsage]
from asset_shepherd.web import create_app

ARN = "arn:aws:secretsmanager:us-east-1:123456789012:secret:asset-shepherd/contest/openai-Ab12Cd"
pytestmark = pytest.mark.usefixtures("inline_upload_checks")
KEY = "sk-placeholder-only-not-a-real-credential"
KIMI = "moonshotai.kimi-k2.5"
LUNA = hosted_models.OPENAI_LUNA_ID


def _settings() -> dict[str, str]:
    return {
        "ASSET_SHEPHERD_MODEL_PROVIDER": "bedrock-converse",
        "ASSET_SHEPHERD_ALLOWED_MODEL_IDS": f"{KIMI},{LUNA}",
        "ASSET_SHEPHERD_AWS_REGION": "us-east-1",
        hosted_models.OPENAI_SECRET_SETTING: ARN,
        "ASSET_SHEPHERD_WORKSPACE_BUCKET": "test-workspace-bucket",
    }


def test_openai_choice_requires_allowlist_and_secret_reference() -> None:
    """Displaying a choice never retrieves a secret; local provider UX is preserved."""
    settings = _settings()
    choices = hosted_models.hosted_model_choices(settings)
    assert [model.model_id for model in choices] == [KIMI, LUNA]
    assert all(ARN not in str(asdict(model)) for model in choices)
    settings.pop(hosted_models.OPENAI_SECRET_SETTING)
    assert [model.model_id for model in hosted_models.hosted_model_choices(settings)] == [KIMI]
    assert hosted_models.hosted_model_choices({"ASSET_SHEPHERD_MODEL_PROVIDER": "openai"}) == ()
    with pytest.raises(ValueError):
        hosted_models.hosted_model_values(LUNA, settings)


def test_luna_uses_exact_secret_and_xhigh_for_both_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credentials remain in the private factory result, not settings or public metadata."""
    calls: list[tuple[str, str, str | None]] = []

    def secret(arn: str, region: str, aws_profile: str | None = None) -> str:
        calls.append((arn, region, aws_profile))
        return KEY

    monkeypatch.setattr(hosted_models, "load_openai_secret", secret)
    settings = _settings()
    settings["ASSET_SHEPHERD_OPENAI_RESPONSES_URL"] = "https://unused.example"
    values = hosted_models.hosted_model_values(LUNA, settings)
    assert calls == [(ARN, "us-east-1", None)]
    assert values["OPENAI_API_KEY"] == KEY
    assert values["ASSET_SHEPHERD_MODEL_PROVIDER"] == "openai"
    assert values["ASSET_SHEPHERD_INTAKE_PROVIDER"] == "openai"
    assert values["ASSET_SHEPHERD_WORKFLOW_REASONING"] == "xhigh"
    assert values["ASSET_SHEPHERD_INTAKE_REASONING"] == "xhigh"
    assert "ASSET_SHEPHERD_OPENAI_RESPONSES_URL" not in values
    assert "OPENAI_API_KEY" not in settings
    assert values["ASSET_SHEPHERD_SESSION_BUCKET"] == "test-workspace-bucket"
    calls.clear()
    kimi = hosted_models.hosted_model_values(KIMI, values)
    assert not calls
    assert "OPENAI_API_KEY" not in kimi
    assert "ASSET_SHEPHERD_WORKFLOW_REASONING" not in kimi
    assert kimi["ASSET_SHEPHERD_MODEL_PROVIDER"] == "bedrock-converse"


def test_runtime_uses_task_role_and_does_not_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same persisted model selects the same provider after runtime replacement."""
    for name, value in _settings().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("AWS_PROFILE", "must-not-use-a-local-profile")

    def secret(arn: str, region: str, aws_profile: str | None = None) -> str:
        assert aws_profile is None
        assert arn == ARN and region == "us-east-1"
        return KEY

    monkeypatch.setattr(hosted_models, "load_openai_secret", secret)
    values = _model_values(LUNA)
    assert values["ASSET_SHEPHERD_MODEL_PROVIDER"] == "openai"
    assert "AWS_PROFILE" not in values
    monkeypatch.setenv("ASSET_SHEPHERD_ALLOWED_MODEL_IDS", KIMI)
    with pytest.raises(ValueError, match="not enabled"):
        _model_values(LUNA)


def test_secret_errors_are_redacted_and_wrong_region_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not expose SDK response bodies or contact a mismatched secret location."""
    with pytest.raises(ValueError, match="Invalid deployment"):
        hosted_models.load_openai_secret(ARN, "us-west-2")

    def failed_session(**kwargs: object) -> None:
        raise RuntimeError(KEY)

    monkeypatch.setattr(hosted_models.boto3, "Session", failed_session)
    with pytest.raises(ValueError, match="could not be loaded") as caught:
        hosted_models.load_openai_secret(ARN, "us-east-1")
    assert KEY not in str(caught.value)
    assert caught.value.__suppress_context__


def test_gallery_lists_explicit_providers_without_loading_or_exposing_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The authenticated gallery's public model metadata never needs a secret read."""
    settings = _settings()
    settings.pop("ASSET_SHEPHERD_WORKSPACE_BUCKET")
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ASSET_SHEPHERD_MODEL_ID", LUNA)

    def no_secret(*args: object, **kwargs: object) -> str:
        raise AssertionError("Listing model choices must not retrieve provider credentials")

    monkeypatch.setattr(hosted_models, "load_openai_secret", no_secret)
    client = TestClient(create_app(work_root=tmp_path))
    response = client.get("/workspace/new/upload")
    assert response.status_code == 200
    assert "Luna xhigh" in response.text and "OpenAI API" in response.text
    assert "Kimi K2.5" in response.text
    assert ARN not in response.text and KEY not in response.text


def test_provider_error_body_and_key_never_enter_public_workflow_error() -> None:
    """A simulated ordinary provider authentication failure exposes only its status."""

    def rejected(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": KEY, "type": "invalid_api_key"}})

    async def invoke() -> None:
        model = CompleteResponseOpenAIModel(
            model_id=LUNA,
            client_args={
                "api_key": KEY,
                "max_retries": 0,
                "http_client": httpx.AsyncClient(transport=httpx.MockTransport(rejected)),
            },
        )
        assert KEY not in str(model.get_config())
        async for _ in model.stream(
            [{"role": "user", "content": [{"text": "Inspect the tablet."}]}]
        ):
            pass

    with pytest.raises(AgentWorkflowError, match="HTTP 401") as caught:
        run(invoke())
    assert KEY not in str(caught.value)
    assert caught.value.__suppress_context__
