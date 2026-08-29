"""M7 acceptance tests for the local Strands agent and native interrupt flow."""

import json
import os
from asyncio import run
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from jsonschema.validators import validator_for
from strands.agent import AgentResult
from strands.types.content import Messages

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError, VerificationFunction
from asset_shepherd.agent_runtime import (
    CompleteResponseBedrockModel,
    CompleteResponseOpenAIModel,
    WorkflowActivityCallback,
    build_environment_model,
    build_live_agent,
    build_scripted_agent,
    load_model_configuration,
)
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentWorkflowResult,
    ApprovalCard,
    Decisions,
    DecisionValue,
    InspectionResult,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.repair import RepairOutcome
from asset_shepherd.verification import verify_repair

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
FIXED_TIME = datetime(2026, 8, 21, 21, 0, tzinfo=UTC)
PACKAGE_NAMES = {
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
}


def test_activity_callback_reports_tools_without_streaming_model_reasoning() -> None:
    """The UI activity boundary exposes tool names, never text or chain-of-thought streams."""
    labels: list[str] = []
    callback = WorkflowActivityCallback(labels.append)
    callback(reasoningText="private reasoning", data="model prose")
    callback(
        event={
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": "inspect_asset_for_job",
                    }
                }
            }
        }
    )
    callback(
        event={
            "contentBlockStart": {
                "start": {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": "inspect_asset_for_job",
                    }
                }
            }
        }
    )

    assert labels == ["Measuring the GLB"]


def _fixed_clock() -> datetime:
    return FIXED_TIME


def _job(
    output: Path,
    *,
    verifier: VerificationFunction = verify_repair,
) -> AgentJob:
    return AgentJob(
        BROKEN_PATH,
        PROFILE_PATH,
        output,
        clock=_fixed_clock,
        verification_function=verifier,
    )


def _approval_card(result: AgentResult) -> tuple[str, ApprovalCard]:
    interrupts = tuple(result.interrupts or ())
    assert len(interrupts) == 1
    interrupt = interrupts[0]
    card = ApprovalCard.model_validate_json(json.dumps(interrupt.reason))
    return interrupt.id, card


def _validate_agent_result_schema(output: Path) -> AgentWorkflowResult:
    artifact = output / "agent_result.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    schema = json.loads(
        (PROJECT_ROOT / "schemas" / "agent_workflow_result.schema.json").read_text(encoding="utf-8")
    )
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator_class(schema).validate(payload)
    return AgentWorkflowResult.model_validate_json(artifact.read_text(encoding="utf-8"))


def test_strands_approve_interrupt_resume_verifies_and_packages(tmp_path: Path) -> None:
    """The real Strands loop pauses once, resumes by ID, and produces the exact package."""
    output = tmp_path / "approve"
    job = _job(output)
    runtime = build_scripted_agent(job)
    assert runtime.agent.agent_id == "asset-shepherd-source"

    interrupted = runtime.start()
    assert interrupted.stop_reason == "interrupt"
    interrupt_id, card = _approval_card(interrupted)
    assert card.candidate_id == "normalize-root-v1"
    assert {component.component for component in card.components} == {
        "scale",
        "orientation",
        "grounding",
    }
    assert not (output / "candidate.glb").exists()
    assert not (output / "decisions.json").exists()

    final_agent_result = runtime.resume(interrupt_id, approved=True)
    assert final_agent_result.stop_reason == "end_turn"
    completed = runtime.complete(final_agent_result)
    assert (
        completed.job_result.verification_state is VerificationState.PASSED_WITH_REMAINING_WARNINGS
    )
    assert completed.metrics.interrupt_count == 1
    assert completed.metrics.provider == "scripted"
    assert completed.metrics.token_usage is not None
    assert completed.metrics.token_usage.total_tokens > 0
    tool_metrics = {metric.name: metric for metric in completed.metrics.tool_calls}
    assert tool_metrics["execute_selected_repairs"].call_count == 2
    assert tool_metrics["execute_selected_repairs"].success_count == 1
    assert tool_metrics["execute_selected_repairs"].error_count == 1
    assert tool_metrics["verify_and_package"].success_count == 1

    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    normalization = next(
        record for record in decisions.records if record.candidate_id == "normalize-root-v1"
    )
    assert normalization.decision is DecisionValue.APPROVED
    assert normalization.interrupt_id == interrupt_id
    with ZipFile(output / "result.zip") as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES
    assert _validate_agent_result_schema(output) == completed


def test_strands_reject_path_preserves_decision_and_findings(tmp_path: Path) -> None:
    """A rejected interrupt records the choice and leaves normalization findings explicit."""
    output = tmp_path / "reject"
    job = _job(output)
    runtime = build_scripted_agent(job)
    interrupted = runtime.start()
    interrupt_id, _ = _approval_card(interrupted)
    completed = runtime.complete(runtime.resume(interrupt_id, approved=False))

    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (output / "provenance.json").read_text(encoding="utf-8")
    )
    verification = VerificationResult.model_validate_json(
        (output / "verification.json").read_text(encoding="utf-8")
    )
    record = next(
        record for record in decisions.records if record.candidate_id == "normalize-root-v1"
    )
    assert record.decision is DecisionValue.REJECTED
    assert record.interrupt_id == interrupt_id
    assert "normalize-root-v1" not in {
        action.candidate_id for action in provenance.executed_actions
    }
    assert {
        "HEIGHT_OUT_OF_RANGE",
        "ORIENTATION_NOT_Y_UP",
        "NOT_GROUNDED",
    } <= {warning.partition(":")[0] for warning in verification.remaining_warnings}
    assert (
        completed.job_result.verification_state is VerificationState.PASSED_WITH_REMAINING_WARNINGS
    )
    repaired = inspect_asset(output / "repaired.glb", job.profile)
    assert repaired.geometry is not None
    assert repaired.geometry.dominant_dimension_axis == "X"
    assert repaired.geometry.ground_relationship == "FLOATS_ABOVE"


def test_agent_rejects_wrong_interrupt_id_and_unapproved_direct_execution(
    tmp_path: Path,
) -> None:
    """Neither caller nor model can bypass the exact interrupt-bound authorization."""
    output = tmp_path / "wrong-id"
    job = _job(output)
    runtime = build_scripted_agent(job)
    interrupted = runtime.start()
    interrupt_id, _ = _approval_card(interrupted)
    with pytest.raises(AgentWorkflowError, match="does not match"):
        runtime.resume(f"{interrupt_id}-wrong", approved=True)
    assert not (output / "candidate.glb").exists()

    direct_job = _job(tmp_path / "direct")
    direct_job.inspect()
    plan = direct_job.list_candidates()
    direct_job.select_candidates([candidate.id for candidate in plan.candidates])
    with pytest.raises(AgentWorkflowError, match="no interrupt-bound decision"):
        direct_job.execute(approved=None, interrupt_id=None)
    assert not direct_job.candidate_path.exists()


class _FailOnceVerifier:
    """Inject one controlled failure before delegating to the real verifier."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(
        self,
        source: Path,
        candidate: Path,
        profile: ProjectProfile,
        original: InspectionResult,
        plan: RepairPlan,
        decisions: Decisions,
        outcome: RepairOutcome,
        provenance: Provenance,
    ) -> VerificationResult:
        self.calls += 1
        if self.calls == 1:
            return VerificationResult(
                verification_id="verification-forced-failure-v1",
                source_sha256=outcome.source_sha256,
                output_sha256=outcome.output_sha256,
                state=VerificationState.FAILED,
                checks=(),
                remaining_warnings=("FORCED_TEST_FAILURE: exercise bounded correction",),
                second_plan_candidate_count=1,
            )
        return verify_repair(
            source,
            candidate,
            profile,
            original,
            plan,
            decisions,
            outcome,
            provenance,
        )


def test_agent_reassesses_once_without_reapplying_the_failed_plan(tmp_path: Path) -> None:
    """A failed verification gets one fresh plan assessment and no silent mutation."""
    verifier = _FailOnceVerifier()
    job = _job(tmp_path / "correction", verifier=verifier)
    runtime = build_scripted_agent(job)
    interrupted = runtime.start()
    interrupt_id, _ = _approval_card(interrupted)
    completed = runtime.complete(runtime.resume(interrupt_id, approved=True))

    assert verifier.calls == 1
    assert completed.metrics.correction_attempts == 1
    metrics = {metric.name: metric for metric in completed.metrics.tool_calls}
    assert metrics["reassess_candidate_after_verification_failure"].call_count == 1
    assert metrics["verify_and_package"].call_count == 2
    assert not completed.job_result.ready_candidate
    assert completed.job_result.verification_state is VerificationState.FAILED
    assert job.outcome is not None
    outcome = job.outcome
    assert job.provenance is not None
    assert job.provenance.output_sha256 == outcome.output_sha256
    job.last_verification = VerificationResult(
        verification_id="verification-forced-second-failure-v1",
        source_sha256=outcome.source_sha256,
        output_sha256=outcome.output_sha256,
        state=VerificationState.FAILED,
        checks=(),
        remaining_warnings=(),
        second_plan_candidate_count=1,
    )
    with pytest.raises(AgentWorkflowError, match="already been used"):
        job.reassess_candidate_after_failure()


def test_live_model_configuration_is_explicit_and_offline_tests_need_no_credentials() -> None:
    """No default model ID or credential lookup is needed for the offline harness."""
    with pytest.raises(AgentWorkflowError, match="Missing live model configuration"):
        load_model_configuration({})
    configuration = load_model_configuration(
        {
            "ASSET_SHEPHERD_MODEL_PROVIDER": "bedrock",
            "ASSET_SHEPHERD_MODEL_ID": "configured-by-user",
            "ASSET_SHEPHERD_AWS_REGION": "us-test-1",
            "AWS_PROFILE": "asset-shepherd",
        }
    )
    assert configuration.model_id == "configured-by-user"
    assert configuration.aws_profile == "asset-shepherd"


def test_openai_model_reads_complete_response_before_closing_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local OpenAI bridge avoids the dependency's abandoned SSE-generator cleanup path."""

    class FakeResponses:
        def __init__(self) -> None:
            self.request: dict[str, object] = {}

        async def create(self, **request: object) -> SimpleNamespace:
            self.request = request
            return SimpleNamespace(
                id="response-123",
                status="completed",
                output=(
                    SimpleNamespace(
                        type="message",
                        content=(SimpleNamespace(type="output_text", text="Finished."),),
                    ),
                ),
                usage=SimpleNamespace(input_tokens=7, output_tokens=3, total_tokens=10),
            )

    class FakeAsyncOpenAI:
        instance: "FakeAsyncOpenAI | None" = None

        def __init__(self, **client_args: object) -> None:
            self.client_args = client_args
            self.responses = FakeResponses()
            self.exited = False
            FakeAsyncOpenAI.instance = self

        async def __aenter__(self) -> "FakeAsyncOpenAI":
            return self

        async def __aexit__(self, *_args: object) -> None:
            self.exited = True

    monkeypatch.setattr("asset_shepherd.agent_runtime.openai.AsyncOpenAI", FakeAsyncOpenAI)
    model = CompleteResponseOpenAIModel(
        client_args={"api_key": "test-only"},
        model_id="gpt-test",
        stateful=True,
    )
    messages: Messages = [{"role": "user", "content": [{"text": "Hello"}]}]
    model_state: dict[str, object] = {}

    async def collect() -> list[object]:
        return [event async for event in model.stream(messages, model_state=model_state)]

    events = run(collect())
    client = FakeAsyncOpenAI.instance
    assert client is not None
    assert client.exited
    assert client.responses.request["stream"] is False
    assert client.responses.request["store"] is True
    assert model_state == {"response_id": "response-123"}
    assert events[0] == {"messageStart": {"role": "assistant"}}
    assert {"contentBlockDelta": {"delta": {"text": "Finished."}}} in events


def test_bedrock_workflow_uses_runtime_responses_and_request_scoped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Strands bridge preserves Responses tool semantics without retaining AWS credentials."""

    class FakeResponses:
        def __init__(self) -> None:
            self.request: dict[str, object] = {}

        async def create(self, **request: object) -> SimpleNamespace:
            self.request = request
            return SimpleNamespace(
                id="bedrock-response-123",
                status="completed",
                output=(
                    SimpleNamespace(
                        type="function_call",
                        name="inspect_asset_for_job",
                        arguments="{}",
                        call_id="call-1",
                    ),
                ),
                usage=SimpleNamespace(input_tokens=12, output_tokens=4, total_tokens=16),
            )

    class FakeAsyncOpenAI:
        instance: "FakeAsyncOpenAI | None" = None

        def __init__(self, **client_args: object) -> None:
            self.client_args = client_args
            self.responses = FakeResponses()
            FakeAsyncOpenAI.instance = self

        async def __aenter__(self) -> "FakeAsyncOpenAI":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    token_calls: list[str] = []

    def token_provider(region: str) -> str:
        token_calls.append(region)
        return "request-scoped-test-token"

    monkeypatch.setattr("asset_shepherd.agent_runtime.openai.AsyncOpenAI", FakeAsyncOpenAI)
    model = CompleteResponseBedrockModel(
        model_id="us.openai.gpt-5.6-luna",
        region="us-east-1",
        token_provider=token_provider,
        stateful=True,
        params={"reasoning": {"effort": "xhigh"}, "parallel_tool_calls": False},
    )
    messages: Messages = [{"role": "user", "content": [{"text": "Inspect this asset."}]}]
    model_state: dict[str, object] = {}

    async def collect() -> list[object]:
        return [event async for event in model.stream(messages, model_state=model_state)]

    events = run(collect())
    client = FakeAsyncOpenAI.instance
    assert client is not None
    assert token_calls == ["us-east-1"]
    assert client.client_args == {
        "api_key": "request-scoped-test-token",
        "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1",
    }
    assert client.responses.request["model"] == "us.openai.gpt-5.6-luna"
    assert client.responses.request["store"] is True
    assert client.responses.request["parallel_tool_calls"] is False
    assert model_state == {"response_id": "bedrock-response-123"}
    assert any("toolUse" in json.dumps(event) for event in events)
    assert "request-scoped-test-token" not in repr(model.get_config())


def test_environment_model_builds_bedrock_responses_not_converse() -> None:
    """The production Bedrock selection resolves to the parity Responses adapter."""
    model, configuration = build_environment_model(
        {
            "ASSET_SHEPHERD_MODEL_PROVIDER": "bedrock",
            "ASSET_SHEPHERD_MODEL_ID": "us.openai.gpt-5.6-luna",
            "ASSET_SHEPHERD_AWS_REGION": "us-east-1",
            "ASSET_SHEPHERD_WORKFLOW_REASONING": "xhigh",
        }
    )

    assert isinstance(model, CompleteResponseBedrockModel)
    assert configuration.provider == "bedrock"
    assert configuration.model_id == "us.openai.gpt-5.6-luna"


def test_persistent_session_requires_both_identity_and_storage(tmp_path: Path) -> None:
    """Scripted and future Bedrock agents share the same explicit session-state contract."""
    job = _job(tmp_path / "session-contract")
    with pytest.raises(AgentWorkflowError, match="both an ID and isolated storage"):
        build_scripted_agent(job, session_id="asset-session")
    with pytest.raises(AgentWorkflowError, match="both an ID and isolated storage"):
        build_scripted_agent(job, session_root=tmp_path / "strands-state")


@pytest.mark.live
def test_opt_in_live_strands_provider_workflow(tmp_path: Path) -> None:
    """Run the same approval flow through the environment-configured live provider when opted in."""
    if os.environ.get("ASSET_SHEPHERD_RUN_LIVE") != "1":
        pytest.skip("set ASSET_SHEPHERD_RUN_LIVE=1 with model configuration to opt in")
    output = tmp_path / "live"
    runtime = build_live_agent(
        _job(output),
        session_id="live-bedrock-test",
        session_root=tmp_path / "live-strands-state",
    )
    interrupted = runtime.start()
    interrupt_id, _ = _approval_card(interrupted)
    completed = runtime.complete(runtime.resume(interrupt_id, approved=True))
    assert completed.job_result.ready_candidate
    assert completed.metrics.provider == "bedrock"
