"""Single-agent Strands orchestration, configuration, and offline harness."""

# The custom Model override signatures intentionally match the SDK's Any-based interface.
# ruff: noqa: ANN401

import json
from collections.abc import AsyncGenerator, AsyncIterable, Mapping
from dataclasses import dataclass
from os import environ
from pathlib import Path
from time import perf_counter
from typing import Any, TypeVar, cast

from pydantic import BaseModel
from strands import Agent
from strands.agent import AgentResult
from strands.models import BedrockModel, Model
from strands.session import SessionManager, SnapshotSessionManager
from strands.storage import LocalFileStorage
from strands.types.agent import AgentInput
from strands.types.content import Messages, SystemContentBlock
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_prompt import (
    AGENT_PROMPT_VERSION,
    AGENT_SYSTEM_PROMPT_V2,
    build_agent_start_prompt,
)
from asset_shepherd.agent_tools import AssetShepherdTools
from asset_shepherd.models import (
    AgentMetrics,
    AgentTokenUsage,
    AgentToolMetric,
    AgentWorkflowResult,
    ApprovalCard,
    ApprovalResponse,
)

T = TypeVar("T", bound=BaseModel)


def _validate_approval_card(value: object) -> ApprovalCard:
    return ApprovalCard.model_validate_json(json.dumps(value))


@dataclass(frozen=True)
class ModelConfiguration:
    """Explicit live-model configuration loaded from environment variables."""

    provider: str
    model_id: str
    region: str
    aws_profile: str | None


def load_model_configuration(
    values: Mapping[str, str] = environ,
) -> ModelConfiguration:
    """Load live provider settings without choosing an implicit model ID."""
    provider = values.get("ASSET_SHEPHERD_MODEL_PROVIDER")
    model_id = values.get("ASSET_SHEPHERD_MODEL_ID")
    region = values.get("ASSET_SHEPHERD_AWS_REGION") or values.get("AWS_REGION")
    missing = [
        name
        for name, value in (
            ("ASSET_SHEPHERD_MODEL_PROVIDER", provider),
            ("ASSET_SHEPHERD_MODEL_ID", model_id),
            ("ASSET_SHEPHERD_AWS_REGION or AWS_REGION", region),
        )
        if not value
    ]
    if missing:
        raise AgentWorkflowError(f"Missing live model configuration: {', '.join(missing)}")
    if provider != "bedrock":
        raise AgentWorkflowError(f"Unsupported live model provider: {provider}")
    return ModelConfiguration(
        provider=provider,
        model_id=cast(str, model_id),
        region=cast(str, region),
        aws_profile=values.get("AWS_PROFILE"),
    )


def build_environment_model(
    values: Mapping[str, str] = environ,
) -> tuple[Model, ModelConfiguration]:
    """Construct the configured provider; invocation remains caller-controlled and opt-in."""
    configuration = load_model_configuration(values)
    model = BedrockModel(
        model_id=configuration.model_id,
        region_name=configuration.region,
    )
    return model, configuration


class ScriptedWorkflowModel(Model):
    """Zero-network model harness that drives the real Strands loop deterministically."""

    def __init__(self, job: AgentJob) -> None:
        """Bind the harness to a single deterministic job state."""
        self.job = job
        self.config: dict[str, Any] = {
            "provider": "scripted",
            "model_id": "asset-shepherd-scripted-v1",
            "context_window_limit": 16_384,
        }
        self._tool_call_count = 0

    def update_config(self, **model_config: Any) -> None:
        """Update harness metadata without changing deterministic behavior."""
        self.config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        """Return a copy of harness configuration."""
        return dict(self.config)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Reject unused structured-output calls in the scripted harness."""
        del output_model, prompt, system_prompt, kwargs
        if False:
            yield {}
        raise NotImplementedError("The workflow harness uses tool calls, not model-only output")

    def _next_action(self) -> tuple[str, dict[str, Any]] | None:
        if self.job.inspection is None:
            return "inspect_asset_for_job", {}
        if self.job.full_plan is None:
            return "list_repair_candidates", {}
        if self.job.selected_plan is None:
            return (
                "select_repair_candidates",
                {"candidate_ids": [candidate.id for candidate in self.job.full_plan.candidates]},
            )
        if self.job.selected_plan.blocked and self.job.result is None:
            return "verify_and_package", {}
        if self.job.outcome is None:
            return "execute_selected_repairs", {}
        if self.job.result is None:
            if self.job.last_verification is not None and self.job.correction_attempts == 0:
                return "reassess_candidate_after_verification_failure", {}
            return "verify_and_package", {}
        return None

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Yield one state-derived tool call or a final grounded summary."""
        del messages, tool_specs, system_prompt, tool_choice, system_prompt_content
        del invocation_state, kwargs
        action = self._next_action()
        yield cast(StreamEvent, {"messageStart": {"role": "assistant"}})
        if action is not None:
            name, arguments = action
            self._tool_call_count += 1
            tool_use_id = f"asset-shepherd-scripted-{self._tool_call_count:02d}"
            yield cast(
                StreamEvent,
                {
                    "contentBlockStart": {
                        "start": {"toolUse": {"toolUseId": tool_use_id, "name": name}}
                    }
                },
            )
            yield cast(
                StreamEvent,
                {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}},
            )
            yield cast(StreamEvent, {"contentBlockStop": {}})
            yield cast(StreamEvent, {"messageStop": {"stopReason": "tool_use"}})
        else:
            if self.job.result is None:
                raise AgentWorkflowError("Scripted agent ended without a deterministic result")
            message = (
                f"Asset Shepherd finished with {self.job.result.verification_state}. "
                f"The result package is {self.job.result.result_zip}."
            )
            yield cast(StreamEvent, {"contentBlockDelta": {"delta": {"text": message}}})
            yield cast(StreamEvent, {"contentBlockStop": {}})
            yield cast(StreamEvent, {"messageStop": {"stopReason": "end_turn"}})
        yield cast(
            StreamEvent,
            {
                "metadata": {
                    "usage": {"inputTokens": 8, "outputTokens": 2, "totalTokens": 10},
                    "metrics": {"latencyMs": 1},
                }
            },
        )


class AssetShepherdAgent:
    """Primary Strands agent with explicit interrupt/resume and structured completion."""

    def __init__(
        self,
        job: AgentJob,
        model: Model,
        *,
        provider: str,
        model_id: str,
        session_manager: SessionManager | None = None,
    ) -> None:
        """Create one primary agent with only the Asset Shepherd tool boundary."""
        self.job = job
        self.provider = provider
        self.model_id = model_id
        self.tools = AssetShepherdTools(job)
        self.agent = Agent(
            model=model,
            tools=self.tools.as_list(),
            system_prompt=AGENT_SYSTEM_PROMPT_V2,
            callback_handler=None,
            load_tools_from_directory=False,
            agent_id=f"asset-shepherd-{job.source.stem}",
            name="Asset Shepherd",
            description="Inspect, safely repair, verify, and package one static GLB.",
            session_manager=session_manager,
        )
        self._invocation_duration_seconds = 0.0
        self._interrupt_count = 1 if job.pending_interrupt_id is not None else 0
        self._latest_result: AgentResult | None = None

    def _invoke(self, prompt: AgentInput) -> AgentResult:
        started = perf_counter()
        try:
            result = self.agent(prompt, limits={"turns": 12})
        finally:
            self._invocation_duration_seconds += perf_counter() - started
        self._latest_result = result
        return result

    def _capture_interrupt(self, result: AgentResult) -> None:
        interrupts = tuple(result.interrupts or ())
        if result.stop_reason != "interrupt" or len(interrupts) != 1:
            raise AgentWorkflowError("Expected exactly one Strands approval interrupt")
        interrupt = interrupts[0]
        _validate_approval_card(interrupt.reason)
        self.job.set_pending_interrupt(interrupt.id)
        self._interrupt_count += 1

    def start(self) -> AgentResult:
        """Start the live Strands loop and surface its approval interrupt."""
        result = self._invoke(
            build_agent_start_prompt(
                self.job.profile,
                asset_intent=self.job.asset_intent,
                profile_policy=self.job.profile_policy,
            )
        )
        if result.stop_reason == "interrupt":
            self._capture_interrupt(result)
        return result

    def resume(self, interrupt_id: str, *, approved: bool) -> AgentResult:
        """Resume only the exact pending Strands interrupt with a validated decision."""
        if self.job.pending_interrupt_id is None:
            raise AgentWorkflowError("No approval interrupt is pending")
        if interrupt_id != self.job.pending_interrupt_id:
            raise AgentWorkflowError(
                "Approval response interrupt ID does not match the pending job"
            )
        latest = self._latest_result
        if latest is None:
            restored_card = self.job.approval_card()
            if restored_card is None:
                raise AgentWorkflowError("The pending interrupt has no approval card")
            card = restored_card
        else:
            card = _validate_approval_card(
                next(
                    interrupt.reason
                    for interrupt in latest.interrupts or ()
                    if interrupt.id == interrupt_id
                )
            )
        response = ApprovalResponse(candidate_id=card.candidate_id, approved=approved)
        result = self._invoke(
            [
                {
                    "interruptResponse": {
                        "interruptId": interrupt_id,
                        "response": response.model_dump(mode="json"),
                    }
                }
            ]
        )
        if result.stop_reason == "interrupt":
            self._capture_interrupt(result)
        else:
            self.job.set_pending_interrupt(None)
        return result

    def complete(self, result: AgentResult | None = None) -> AgentWorkflowResult:
        """Validate deterministic completion and persist structured metrics and explanation."""
        current = result or self._latest_result
        if current is None:
            raise AgentWorkflowError("The agent has not been invoked")
        if current.stop_reason == "interrupt":
            raise AgentWorkflowError("The agent cannot complete while approval is pending")
        if self.job.result is None or self.job.last_verification is None:
            raise AgentWorkflowError(
                "The agent ended before deterministic verification and packaging"
            )
        summary = current.metrics.get_summary()
        usage_value = cast(dict[str, Any], summary.get("accumulated_usage", {}))
        token_usage = AgentTokenUsage(
            input_tokens=int(usage_value.get("inputTokens", 0)),
            output_tokens=int(usage_value.get("outputTokens", 0)),
            total_tokens=int(usage_value.get("totalTokens", 0)),
        )
        tool_usage = cast(dict[str, dict[str, Any]], summary.get("tool_usage", {}))
        tool_metrics = tuple(
            AgentToolMetric(
                name=name,
                call_count=int(values["execution_stats"]["call_count"]),
                success_count=int(values["execution_stats"]["success_count"]),
                error_count=int(values["execution_stats"]["error_count"]),
                duration_seconds=float(values["execution_stats"]["total_time"]),
            )
            for name, values in sorted(tool_usage.items())
        )
        metrics = AgentMetrics(
            provider=self.provider,
            model_id=self.model_id,
            invocation_duration_seconds=self._invocation_duration_seconds,
            token_usage=token_usage,
            tool_calls=tool_metrics,
            interrupt_count=self._interrupt_count,
            correction_attempts=self.job.correction_attempts,
            final_verification_state=self.job.last_verification.state,
        )
        workflow_result = AgentWorkflowResult(
            prompt_version=AGENT_PROMPT_VERSION,
            job_result=self.job.result,
            user_message=str(current).strip(),
            metrics=metrics,
        )
        output_path = self.job.output_dir / "agent_result.json"
        output_path.write_text(
            f"{json.dumps(workflow_result.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
            encoding="utf-8",
            newline="\n",
        )
        return workflow_result

    def run(self, *, approved: bool) -> AgentWorkflowResult:
        """Run through one native interrupt and resume for local CLI use."""
        result = self.start()
        if result.stop_reason == "interrupt":
            interrupt = next(iter(result.interrupts or ()))
            result = self.resume(interrupt.id, approved=approved)
        return self.complete(result)


def _snapshot_session_manager(
    session_id: str | None,
    session_root: Path | None,
) -> SessionManager | None:
    """Build one provider-neutral durable Strands session when requested."""
    if session_id is None and session_root is None:
        return None
    if session_id is None or session_root is None:
        raise AgentWorkflowError("A persistent session requires both an ID and isolated storage")
    return SnapshotSessionManager(
        session_id,
        storage=LocalFileStorage(str(session_root.resolve(strict=False))),
        save_latest_on="invocation",
    )


def build_live_agent(
    job: AgentJob,
    *,
    session_id: str | None = None,
    session_root: Path | None = None,
) -> AssetShepherdAgent:
    """Build a live environment-configured agent with optional durable session state."""
    model, configuration = build_environment_model()
    return AssetShepherdAgent(
        job,
        model,
        provider=configuration.provider,
        model_id=configuration.model_id,
        session_manager=_snapshot_session_manager(session_id, session_root),
    )


def build_scripted_agent(
    job: AgentJob,
    *,
    session_id: str | None = None,
    session_root: Path | None = None,
) -> AssetShepherdAgent:
    """Build the zero-network harness over the real Strands agent runtime."""
    model = ScriptedWorkflowModel(job)
    return AssetShepherdAgent(
        job,
        model,
        provider="scripted",
        model_id="asset-shepherd-scripted-v1",
        session_manager=_snapshot_session_manager(session_id, session_root),
    )
