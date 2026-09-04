"""Typed Amazon Bedrock AgentCore boundary for durable hosted-workspace commands."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, cast

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from asset_shepherd.bedrock_converse import resolve_bedrock_converse_model
from asset_shepherd.cloud_workspace import S3DynamoWorkspaceRepository
from asset_shepherd.hosted_workspace import (
    HostedWorkspace,
    HostedWorkspaceError,
    HostedWorkspaceStore,
)
from asset_shepherd.intake_analyzer import DeterministicTargetIntakeAnalyzer
from asset_shepherd.models import ProjectProfile, ProposalResponse

_ID_PATTERN = r"^[0-9a-f]{32}$"
_OWNER_PATTERN = r"^[a-z0-9_.-]{2,80}$"
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RuntimeConfigurationError(RuntimeError):
    """Raised when deployment-owned AgentCore configuration is incomplete."""


class RuntimeInvocationError(ValueError):
    """Raised for a safe, caller-visible structured invocation rejection."""


class _CommandBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    actor_id: str = Field(pattern=_OWNER_PATTERN)
    workspace_id: str = Field(pattern=_ID_PATTERN)
    command_id: str = Field(pattern=_ID_PATTERN)


class StatusCommand(_CommandBase):
    """Read the current durable workflow state without advancing it."""

    operation: Literal["status"]


class ConfirmTargetCommand(_CommandBase):
    """Freeze the already-collected target and begin the first agent turn."""

    operation: Literal["confirm_target"]
    accept_supported_goal: bool
    viewing_use: str | None = Field(default=None, max_length=40)
    custom_values: dict[str, str | None] | None = None

    @field_validator("custom_values")
    @classmethod
    def bound_custom_values(
        cls, value: dict[str, str | None] | None
    ) -> dict[str, str | None] | None:
        """Keep the advanced policy form bounded before it reaches the workflow."""
        if value is None:
            return None
        if len(value) > 32:
            raise ValueError("Too many custom policy values")
        if any(
            len(key) > 80 or (item is not None and len(item) > 200) for key, item in value.items()
        ):
            raise ValueError("A custom policy value is too long")
        return value


class DecisionCommand(_CommandBase):
    """Resolve the exact pending mutation interrupt."""

    operation: Literal["decision"]
    interrupt_id: str = Field(min_length=8, max_length=160)
    approved: bool


class RevisePlanCommand(_CommandBase):
    """Return typed proposal feedback without authorizing a mutation."""

    operation: Literal["revise_plan"]
    interrupt_id: str = Field(min_length=8, max_length=160)
    responses: tuple[ProposalResponse, ...] = Field(min_length=1, max_length=16)


class ReviewResultCommand(_CommandBase):
    """Accept a result or start one bounded refinement turn."""

    operation: Literal["review_result"]
    accepted: bool
    feedback: str = Field(default="", max_length=2000)
    continuation_source: Literal["INPUT", "CANDIDATE"] = "CANDIDATE"


class RetryCommand(_CommandBase):
    """Retry only an existing deterministically recoverable incomplete turn."""

    operation: Literal["retry"]


RuntimeCommand = Annotated[
    StatusCommand
    | ConfirmTargetCommand
    | DecisionCommand
    | RevisePlanCommand
    | ReviewResultCommand
    | RetryCommand,
    Field(discriminator="operation"),
]
_COMMAND_ADAPTER: TypeAdapter[RuntimeCommand] = TypeAdapter(RuntimeCommand)


def validate_runtime_command(payload: object) -> RuntimeCommand:
    """Validate one public runtime command for trusted callers and dispatchers."""
    try:
        return _COMMAND_ADAPTER.validate_python(payload)
    except ValueError as error:
        raise RuntimeInvocationError("The runtime command is invalid.") from error


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeConfigurationError(f"Missing deployment configuration: {name}")
    return value


def _model_values(model_id: str) -> dict[str, str]:
    """Resolve one persisted, allowlisted Bedrock model without accepting provider input."""
    capability = resolve_bedrock_converse_model(model_id)
    allowed_models = {
        value.strip()
        for value in os.environ.get("ASSET_SHEPHERD_ALLOWED_MODEL_IDS", "").split(",")
        if value.strip()
    }
    if allowed_models and capability.model_id not in allowed_models:
        raise RuntimeConfigurationError("The workspace model is not enabled in this deployment")
    values = dict(os.environ)
    values["ASSET_SHEPHERD_MODEL_PROVIDER"] = "bedrock-converse"
    values["ASSET_SHEPHERD_INTAKE_PROVIDER"] = "bedrock-converse"
    values["ASSET_SHEPHERD_MODEL_ID"] = capability.model_id
    values["ASSET_SHEPHERD_INTAKE_MODEL"] = capability.model_id
    values.setdefault(
        "ASSET_SHEPHERD_SESSION_BUCKET",
        _required_environment("ASSET_SHEPHERD_WORKSPACE_BUCKET"),
    )
    values.pop("AWS_PROFILE", None)
    return values


@lru_cache(maxsize=1)
def build_runtime_store() -> HostedWorkspaceStore:
    """Build one replaceable cache over the authoritative S3/DynamoDB state."""
    bucket = _required_environment("ASSET_SHEPHERD_WORKSPACE_BUCKET")
    table = _required_environment("ASSET_SHEPHERD_WORKSPACE_TABLE")
    owner_id = _required_environment("ASSET_SHEPHERD_WORKSPACE_OWNER_ID")
    region = (
        os.environ.get("ASSET_SHEPHERD_AWS_REGION", "").strip()
        or os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "").strip()
    )
    if not region:
        raise RuntimeConfigurationError("Missing deployment configuration: AWS region")
    work_root_value = os.environ.get("ASSET_SHEPHERD_RUNTIME_WORK_ROOT", "").strip()
    work_root = (
        Path(work_root_value)
        if work_root_value
        else Path(tempfile.gettempdir()) / "asset-shepherd-agentcore"
    ).resolve(strict=False)
    if not work_root.is_absolute():
        raise RuntimeConfigurationError("The AgentCore cache root must be absolute")
    profile_path = Path(__file__).parent / "data" / "unreal_static_game_asset_family.json"
    profile = ProjectProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
    repository = S3DynamoWorkspaceRepository(
        bucket=bucket,
        table=table,
        owner_id=owner_id,
        region=region,
    )
    try:
        max_turns = int(os.environ.get("ASSET_SHEPHERD_MAX_TURNS", "5"))
    except ValueError as error:
        raise RuntimeConfigurationError("ASSET_SHEPHERD_MAX_TURNS must be an integer") from error
    return HostedWorkspaceStore(
        work_root / "hosted",
        profile,
        DeterministicTargetIntakeAnalyzer(),
        max_turns,
        model_values_factory=_model_values,
        workspace_repository=repository,
    )


def _public_state(workspace: HostedWorkspace) -> dict[str, object]:
    job = workspace.runtime.job if workspace.runtime is not None else None
    result = job.result if job is not None else None
    return {
        "schema_version": 1,
        "workspace_id": workspace.record.workspace_id,
        "record_version": workspace.record.record_version,
        "phase": workspace.record.phase.value,
        "pending_interrupt_id": workspace.record.pending_interrupt_id,
        "accepted": workspace.record.accepted,
        "ready_candidate": workspace.ready_candidate,
        "turn_index": job.turn_index if job is not None else 0,
        "result_id": result.job_id if result is not None else None,
        "error": workspace.record.error,
    }


def execute_runtime_command(
    payload: object,
    *,
    store: HostedWorkspaceStore,
    configured_actor_id: str,
    session_id: str | None = None,
) -> dict[str, object]:
    """Validate and execute exactly one workspace-scoped AgentCore command."""
    command = validate_runtime_command(payload)
    if command.actor_id != configured_actor_id:
        raise RuntimeInvocationError("The runtime actor is not authorized for this workspace.")
    expected_session_id = f"workspace-{command.workspace_id}"
    if session_id and session_id != expected_session_id:
        raise RuntimeInvocationError("The AgentCore session does not match this workspace.")
    workspace = store.get(command.workspace_id)
    if workspace is None:
        raise RuntimeInvocationError("The workspace does not exist or is no longer active.")
    try:
        if isinstance(command, ConfirmTargetCommand):
            workspace = store.confirm_target(
                workspace,
                accept_supported_goal=command.accept_supported_goal,
                command_id=command.command_id,
                viewing_use_value=command.viewing_use,
                custom_values=command.custom_values,
            )
        elif isinstance(command, DecisionCommand):
            workspace = store.decide(
                workspace,
                interrupt_id=command.interrupt_id,
                approved=command.approved,
                command_id=command.command_id,
            )
        elif isinstance(command, RevisePlanCommand):
            workspace = store.revise_plan(
                workspace,
                interrupt_id=command.interrupt_id,
                responses=command.responses,
                command_id=command.command_id,
            )
        elif isinstance(command, ReviewResultCommand):
            workspace = store.review_result(
                workspace,
                accepted=command.accepted,
                feedback=command.feedback,
                command_id=command.command_id,
                continuation_source=command.continuation_source,
            )
        elif isinstance(command, RetryCommand):
            workspace = store.retry_incomplete_turn(workspace, command_id=command.command_id)
    except HostedWorkspaceError as error:
        raise RuntimeInvocationError(str(error)) from error
    return {"ok": True, "state": _public_state(workspace)}


app = BedrockAgentCoreApp()


@app.entrypoint  # pyright: ignore[reportUnknownMemberType]
def invoke(payload: object, context: object) -> dict[str, object]:
    """Execute a typed workspace command through AgentCore's HTTP service contract."""
    session_id_value = getattr(context, "session_id", None)
    session_id = session_id_value if isinstance(session_id_value, str) else None
    started = time.perf_counter()
    correlation: dict[str, object] = {"event": "agentcore_command"}
    try:
        command = validate_runtime_command(payload)
        correlation.update(
            {
                "workspace_id": command.workspace_id,
                "command_id": command.command_id,
                "operation": command.operation,
            }
        )
        logger.info("%s", json.dumps({**correlation, "state": "STARTED"}, sort_keys=True))
        result = execute_runtime_command(
            payload,
            store=build_runtime_store(),
            configured_actor_id=_required_environment("ASSET_SHEPHERD_WORKSPACE_OWNER_ID"),
            session_id=session_id,
        )
        state = result.get("state")
        phase: object = None
        if isinstance(state, dict):
            phase = cast(dict[str, object], state).get("phase")
        logger.info(
            "%s",
            json.dumps(
                {
                    **correlation,
                    "state": "SUCCEEDED",
                    "phase": phase,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                },
                sort_keys=True,
            ),
        )
        return result
    except (RuntimeConfigurationError, RuntimeInvocationError) as error:
        logger.warning(
            "%s",
            json.dumps(
                {
                    **correlation,
                    "state": "REJECTED",
                    "error_type": type(error).__name__,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                },
                sort_keys=True,
            ),
        )
        return {"ok": False, "error": str(error)}


if __name__ == "__main__":
    app.run()  # pyright: ignore[reportUnknownMemberType]
