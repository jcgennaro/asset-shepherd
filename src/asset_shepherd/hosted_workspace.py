"""Durable local reference implementation of the D019 hosted job contract."""

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import BinaryIO
from uuid import uuid4

from pydantic import Field, JsonValue
from strands.agent import AgentResult

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, build_scripted_agent
from asset_shepherd.inspector import preflight_asset
from asset_shepherd.intent import (
    build_asset_intent,
    normalize_intent_description,
)
from asset_shepherd.models import (
    AgentWorkflowResult,
    AssetIntentProvenance,
    AssetTargetUse,
    ContractModel,
    PreflightResult,
    ProfilePolicyProvenance,
    ProjectProfile,
    RepairEligibility,
)
from asset_shepherd.policy_resolution import PolicyResolution, resolve_policy_family
from asset_shepherd.target_intake import (
    TargetIntakeContract,
    clarify_target_intake,
    draft_target_intake,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_EVENTS = 64
WORKSPACE_RETENTION = timedelta(days=7)
_WORKSPACE_ID = re.compile(r"^[0-9a-f]{32}$")
_COMMAND_ID = re.compile(r"^[0-9a-f]{32}$")


class WorkspacePhase(StrEnum):
    """Durable phase of one hosted asset conversation."""

    TARGET_CONFIRMATION = "TARGET_CONFIRMATION"
    APPROVAL = "APPROVAL"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class SupportedJobGoal(StrEnum):
    """Narrow job outcomes the current deterministic core can actually support."""

    STATIC_MESH_READY = "STATIC_MESH_READY"
    STATIC_MESH_FOR_EXTERNAL_RIGGING = "STATIC_MESH_FOR_EXTERNAL_RIGGING"
    INSPECTION_ONLY = "INSPECTION_ONLY"


class SupportStatus(StrEnum):
    """Relationship between original intent and the supported current job."""

    FULL = "FULL"
    NARROWED_EXTERNAL_HANDOFF = "NARROWED_EXTERNAL_HANDOFF"
    INSPECTION_ONLY = "INSPECTION_ONLY"


class WorkspaceEvent(ContractModel):
    """Minimized structured event; routine prose and raw transcript are excluded."""

    sequence: int = Field(ge=1)
    event_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_type: str
    occurred_at: datetime
    evidence_refs: tuple[str, ...] = ()
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class TargetContract(ContractModel):
    """User-confirmed target separated from the supported deterministic job goal."""

    original_intent: str = Field(min_length=12, max_length=600)
    requested_use: AssetTargetUse
    target_height_cm: float = Field(gt=0.0, le=100000.0)
    supported_job_goal: SupportedJobGoal
    support_status: SupportStatus
    external_handoffs: tuple[str, ...] = ()
    confirmed_at: datetime
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceAnswer(ContractModel):
    """Bounded evidence response that stores no raw user question or generated rationale."""

    category: str
    title: str
    statements: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    answered_at: datetime


class HostedWorkspaceRecord(ContractModel):
    """Private, durable source of record for one hosted job conversation."""

    schema_version: int = 1
    workspace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    created_at: datetime
    updated_at: datetime
    retention_expires_at: datetime
    deletion_status: str = "ACTIVE"
    phase: WorkspacePhase
    original_filename: str
    private_description: str = Field(min_length=12, max_length=600)
    preflight: PreflightResult
    target_draft: TargetIntakeContract | None = None
    target: TargetContract | None = None
    intent: AssetIntentProvenance | None = None
    profile_policy: ProfilePolicyProvenance | None = None
    profile_name: str | None = None
    pending_interrupt_id: str | None = None
    error: str | None = None
    processed_commands: dict[str, str] = Field(default_factory=dict)
    events: tuple[WorkspaceEvent, ...] = ()
    last_answer: EvidenceAnswer | None = None


@dataclass
class HostedWorkspace:
    """Loaded durable record plus its reconstructed local Strands runtime."""

    record: HostedWorkspaceRecord
    root: Path
    runtime: AssetShepherdAgent | None = None
    latest_result: AgentResult | None = None
    workflow_result: AgentWorkflowResult | None = None

    @property
    def source_path(self) -> Path:
        """Return the immutable source path for this workspace."""
        return self.root / "source.glb"

    @property
    def output_dir(self) -> Path:
        """Return the deterministic output directory."""
        return self.root / "output"

    @property
    def waiting_for_approval(self) -> bool:
        """Return whether the exact reconstructed runtime has a pending interrupt."""
        return bool(self.runtime and self.runtime.job.pending_interrupt_id)

    @property
    def ready_candidate(self) -> bool:
        """Return whether a verified candidate exists and is marked ready."""
        return bool(
            self.runtime
            and self.runtime.job.result
            and self.runtime.job.result.ready_candidate
            and (self.output_dir / "repaired.glb").is_file()
        )


class HostedWorkspaceError(ValueError):
    """Safe user-facing hosted-workspace validation failure."""


def _write_json_atomic(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(f"{payload}\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def _copy_validated_upload(stream: BinaryIO, destination: Path) -> None:
    total = 0
    header = b""
    with destination.open("xb") as target:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HostedWorkspaceError("The GLB exceeds the 50 MB hosted limit.")
            if len(header) < 4:
                header = (header + chunk)[:4]
            target.write(chunk)
    if total < 12 or header != b"glTF":
        raise HostedWorkspaceError("The upload is not a GLB 2.0 binary container.")


def _canonical_sha256(value: Mapping[str, JsonValue]) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


class HostedWorkspaceStore:
    """Filesystem-backed D019 state with restart-safe Strands reconstruction."""

    def __init__(self, work_root: Path, family: ProjectProfile) -> None:
        """Bind durable workspaces to one trusted parameterized policy family."""
        self.work_root = work_root.resolve(strict=False)
        self.family = family
        self._lock = RLock()

    def _record_path(self, workspace_id: str) -> Path:
        if _WORKSPACE_ID.fullmatch(workspace_id) is None:
            raise HostedWorkspaceError("The workspace identifier is invalid.")
        return self.work_root / workspace_id / "workspace.json"

    def _persist(self, workspace: HostedWorkspace) -> None:
        workspace.record = workspace.record.model_copy(update={"updated_at": datetime.now(UTC)})
        _write_json_atomic(
            workspace.root / "workspace.json",
            workspace.record.model_dump(mode="json"),
        )

    def _append_event(
        self,
        record: HostedWorkspaceRecord,
        event_type: str,
        *,
        evidence_refs: tuple[str, ...] = (),
        payload: Mapping[str, JsonValue] | None = None,
    ) -> HostedWorkspaceRecord:
        values = dict(payload or {})
        sequence = record.events[-1].sequence + 1 if record.events else 1
        event_id = _canonical_sha256(
            {
                "workspace_id": record.workspace_id,
                "sequence": sequence,
                "event_type": event_type,
                "evidence_refs": list(evidence_refs),
                "payload": values,
            }
        )
        event = WorkspaceEvent(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            evidence_refs=evidence_refs,
            payload=values,
        )
        events = (*record.events, event)[-MAX_EVENTS:]
        return record.model_copy(update={"events": events})

    def create(
        self,
        description: str,
        original_filename: str,
        stream: BinaryIO,
    ) -> HostedWorkspace:
        """Create a workspace and run only profile-free objective preflight."""
        normalized = normalize_intent_description(description)
        if Path(original_filename).suffix.lower() != ".glb":
            raise HostedWorkspaceError("Choose exactly one file with a .glb extension.")
        workspace_id = uuid4().hex
        root = self.work_root / workspace_id
        root.mkdir(parents=True, exist_ok=False)
        source_path = root / "source.glb"
        try:
            _copy_validated_upload(stream, source_path)
            preflight = preflight_asset(source_path)
            _write_json_atomic(root / "preflight.json", preflight.model_dump(mode="json"))
            target_draft = draft_target_intake(normalized)
            _write_json_atomic(
                root / "target_intake.json",
                target_draft.model_dump(mode="json"),
            )
            now = datetime.now(UTC)
            record = HostedWorkspaceRecord(
                workspace_id=workspace_id,
                created_at=now,
                updated_at=now,
                retention_expires_at=now + WORKSPACE_RETENTION,
                phase=(
                    WorkspacePhase.TARGET_CONFIRMATION
                    if preflight.package.parse_success
                    else WorkspacePhase.ERROR
                ),
                original_filename=Path(original_filename).name,
                private_description=normalized,
                preflight=preflight,
                target_draft=target_draft,
                error=(
                    None
                    if preflight.package.parse_success
                    else f"Preflight could not read this GLB: {preflight.parse_error}"
                ),
            )
            record = self._append_event(
                record,
                "SOURCE_MEASURED",
                evidence_refs=(preflight.preflight_id, preflight.package.file_sha256),
                payload={
                    "parse_success": preflight.package.parse_success,
                    "structural_eligibility": preflight.structural_eligibility.value,
                },
            )
            workspace = HostedWorkspace(record=record, root=root)
            self._persist(workspace)
            return workspace
        except Exception:
            source_path.unlink(missing_ok=True)
            (root / "preflight.json").unlink(missing_ok=True)
            (root / "target_intake.json").unlink(missing_ok=True)
            (root / "workspace.json").unlink(missing_ok=True)
            root.rmdir()
            raise

    @staticmethod
    def _custom_float(values: Mapping[str, str | None], key: str, label: str) -> float | None:
        raw = values.get(key)
        if raw is None or not raw.strip():
            return None
        try:
            value = float(raw)
        except ValueError as error:
            raise HostedWorkspaceError(f"{label} must be a number.") from error
        if not math.isfinite(value):
            raise HostedWorkspaceError(f"{label} must be finite.")
        return value

    @staticmethod
    def _custom_int(values: Mapping[str, str | None], key: str, label: str) -> int | None:
        raw = values.get(key)
        if raw is None or not raw.strip():
            return None
        try:
            return int(raw)
        except ValueError as error:
            raise HostedWorkspaceError(f"{label} must be a whole number.") from error

    @staticmethod
    def _custom_bool(values: Mapping[str, str | None], key: str, label: str) -> bool | None:
        raw = values.get(key)
        if raw is None or not raw.strip():
            return None
        if raw not in {"true", "false"}:
            raise HostedWorkspaceError(f"{label} must be yes or no.")
        return raw == "true"

    def _derive_profile(
        self,
        description: str,
        target_use: AssetTargetUse,
        target_height_cm: float,
        custom_values: Mapping[str, str | None] | None = None,
    ) -> PolicyResolution:
        """Resolve confirmed intent through the one family plus supported user edits."""
        overrides: dict[str, JsonValue] = {}
        values = custom_values or {}
        supported: tuple[tuple[str, JsonValue | None], ...] = (
            (
                "expected_height_cm.tolerance",
                self._custom_float(values, "custom_height_tolerance_cm", "Height tolerance"),
            ),
            (
                "orientation.require_y_up_geometry",
                self._custom_bool(values, "custom_require_y_up", "Y-up requirement"),
            ),
            (
                "orientation.require_ground_contact",
                self._custom_bool(
                    values,
                    "custom_require_ground_contact",
                    "Ground-contact requirement",
                ),
            ),
            (
                "orientation.ground_tolerance_cm",
                self._custom_float(values, "custom_ground_tolerance_cm", "Ground tolerance"),
            ),
            (
                "budgets.max_triangles",
                self._custom_int(values, "custom_max_triangles", "Triangle budget"),
            ),
            (
                "budgets.max_materials",
                self._custom_int(values, "custom_max_materials", "Material budget"),
            ),
            (
                "budgets.max_textures",
                self._custom_int(values, "custom_max_textures", "Texture budget"),
            ),
            (
                "budgets.max_texture_dimension",
                self._custom_int(
                    values,
                    "custom_max_texture_dimension",
                    "Texture-dimension budget",
                ),
            ),
        )
        for path, value in supported:
            if value is not None:
                overrides[path] = value
        naming_pattern = values.get("custom_naming_pattern")
        if naming_pattern is not None and naming_pattern.strip():
            overrides["naming.pattern"] = naming_pattern.strip()
        try:
            return resolve_policy_family(
                self.family,
                description=description,
                target_use=target_use,
                target_height_cm=target_height_cm,
                user_overrides=overrides,
            )
        except ValueError as error:
            raise HostedWorkspaceError(f"The resolved policy is invalid: {error}") from error

    def clarify_target(
        self,
        workspace: HostedWorkspace,
        *,
        target_use_value: str | None,
        target_height_m: str | None,
        command_id: str,
    ) -> HostedWorkspace:
        """Persist answers only for required target fields missing from the extracted contract."""
        if _COMMAND_ID.fullmatch(command_id) is None:
            raise HostedWorkspaceError("The clarification command identifier is invalid.")
        with self._lock:
            if command_id in workspace.record.processed_commands:
                return workspace
            if workspace.record.phase is not WorkspacePhase.TARGET_CONFIRMATION:
                raise HostedWorkspaceError("This workspace target is already frozen.")
            if workspace.record.target_draft is None:
                raise HostedWorkspaceError("The minimum target contract is unavailable.")
            completed_fields: list[JsonValue] = list(workspace.record.target_draft.missing_fields)
            try:
                target_draft = clarify_target_intake(
                    workspace.record.target_draft,
                    target_use_value=target_use_value,
                    target_height_m=target_height_m,
                )
            except ValueError as error:
                raise HostedWorkspaceError(str(error)) from error
            processed = {**workspace.record.processed_commands, command_id: "TARGET_CLARIFIED"}
            workspace.record = workspace.record.model_copy(
                update={"target_draft": target_draft, "processed_commands": processed}
            )
            workspace.record = self._append_event(
                workspace.record,
                "TARGET_CLARIFIED",
                payload={"completed_fields": completed_fields},
            )
            _write_json_atomic(
                workspace.root / "target_intake.json",
                target_draft.model_dump(mode="json"),
            )
            self._persist(workspace)
            return workspace

    def _target_contract(
        self,
        record: HostedWorkspaceRecord,
        target_use: AssetTargetUse,
        target_height_cm: float,
        accept_supported_goal: bool,
    ) -> TargetContract:
        if record.preflight.structural_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH:
            goal = SupportedJobGoal.INSPECTION_ONLY
            status = SupportStatus.INSPECTION_ONLY
            handoffs = ("Structural repair requires a supported static GLB export.",)
        elif target_use is AssetTargetUse.STATIC_GAME_ASSET:
            goal = SupportedJobGoal.STATIC_MESH_READY
            status = SupportStatus.FULL
            handoffs = ()
        else:
            goal = SupportedJobGoal.STATIC_MESH_FOR_EXTERNAL_RIGGING
            status = SupportStatus.NARROWED_EXTERNAL_HANDOFF
            handoffs = ("Rigging, skinning, and animation remain an external handoff.",)
        if status is not SupportStatus.FULL and not accept_supported_goal:
            raise HostedWorkspaceError(
                "Accept the narrower supported static-mesh or inspection-only goal to continue."
            )
        canonical = _canonical_sha256(
            {
                "original_intent_sha256": sha256(
                    record.private_description.encode("utf-8")
                ).hexdigest(),
                "requested_use": target_use.value,
                "target_height_cm": target_height_cm,
                "supported_job_goal": goal.value,
                "support_status": status.value,
                "external_handoffs": list(handoffs),
            }
        )
        return TargetContract(
            original_intent=record.private_description,
            requested_use=target_use,
            target_height_cm=target_height_cm,
            supported_job_goal=goal,
            support_status=status,
            external_handoffs=handoffs,
            confirmed_at=datetime.now(UTC),
            canonical_sha256=canonical,
        )

    def confirm_target(
        self,
        workspace: HostedWorkspace,
        *,
        accept_supported_goal: bool,
        command_id: str,
        custom_values: Mapping[str, str | None] | None = None,
    ) -> HostedWorkspace:
        """Freeze typed target/policy state and start the unchanged deterministic pipeline."""
        if _COMMAND_ID.fullmatch(command_id) is None:
            raise HostedWorkspaceError("The confirmation command identifier is invalid.")
        with self._lock:
            if command_id in workspace.record.processed_commands:
                return workspace
            if workspace.record.phase is not WorkspacePhase.TARGET_CONFIRMATION:
                raise HostedWorkspaceError("This workspace target is already frozen.")
            target_draft = workspace.record.target_draft
            if target_draft is None or not target_draft.ready_for_confirmation:
                raise HostedWorkspaceError(
                    "Answer the remaining target questions before confirming this job."
                )
            target_use = target_draft.target_use
            target_height_cm = target_draft.target_height_cm
            if target_use is None or target_height_cm is None:
                raise HostedWorkspaceError("The minimum target contract is incomplete.")
            target = self._target_contract(
                workspace.record,
                target_use,
                target_height_cm,
                accept_supported_goal,
            )
            resolution = self._derive_profile(
                workspace.record.private_description,
                target_use,
                target_height_cm,
                custom_values,
            )
            profile = resolution.profile
            policy = resolution.provenance
            profile_name = resolution.display_name
            intent = build_asset_intent(
                workspace.record.private_description,
                target_use,
                target_height_cm,
                intent_id=workspace.record.workspace_id,
            )
            _write_json_atomic(workspace.root / "profile.json", profile.model_dump(mode="json"))
            _write_json_atomic(workspace.root / "intent.json", intent.model_dump(mode="json"))
            processed = {**workspace.record.processed_commands, command_id: "TARGET_CONFIRMED"}
            workspace.record = workspace.record.model_copy(
                update={
                    "target": target,
                    "intent": intent,
                    "profile_policy": policy,
                    "profile_name": profile_name,
                    "processed_commands": processed,
                }
            )
            rule_sources_json: dict[str, JsonValue] = {
                path: source for path, source in policy.rule_sources.items()
            }
            event_payload: dict[str, JsonValue] = {
                "requested_use": target.requested_use.value,
                "supported_job_goal": target.supported_job_goal.value,
                "support_status": target.support_status.value,
                "target_height_cm": target.target_height_cm,
                "frozen_profile_id": policy.frozen_profile_id,
                "base_preset_id": policy.base_preset_id,
                "policy_family_id": policy.policy_family_id,
                "explicit_overrides": policy.explicit_overrides,
                "rule_sources": rule_sources_json,
            }
            workspace.record = self._append_event(
                workspace.record,
                "TARGET_CONFIRMED",
                evidence_refs=(target.canonical_sha256, policy.canonical_sha256),
                payload=event_payload,
            )
            self._persist(workspace)
            runtime = build_scripted_agent(
                AgentJob(
                    workspace.source_path,
                    workspace.root / "profile.json",
                    workspace.output_dir,
                    profile_policy=policy,
                    asset_intent=intent,
                ),
                session_id=workspace.record.workspace_id,
                session_root=workspace.root / "strands_state",
            )
            workspace.runtime = runtime
            try:
                workspace.latest_result = runtime.start()
                if workspace.latest_result.stop_reason != "interrupt":
                    workspace.workflow_result = runtime.complete(workspace.latest_result)
            except Exception as error:
                workspace.record = workspace.record.model_copy(
                    update={"phase": WorkspacePhase.ERROR, "error": str(error)}
                )
            self._sync_runtime(workspace)
            self._record_runtime_events(workspace)
            self._persist(workspace)
            return workspace

    def _load_runtime(self, workspace: HostedWorkspace) -> None:
        record = workspace.record
        if record.intent is None or record.profile_policy is None:
            return
        workspace.runtime = build_scripted_agent(
            AgentJob(
                workspace.source_path,
                workspace.root / "profile.json",
                workspace.output_dir,
                profile_policy=record.profile_policy,
                asset_intent=record.intent,
            ),
            session_id=record.workspace_id,
            session_root=workspace.root / "strands_state",
        )
        result_path = workspace.output_dir / "agent_result.json"
        if result_path.is_file():
            workspace.workflow_result = AgentWorkflowResult.model_validate_json(
                result_path.read_text(encoding="utf-8")
            )

    def _sync_runtime(self, workspace: HostedWorkspace) -> None:
        runtime = workspace.runtime
        if runtime is None:
            return
        job = runtime.job
        if job.pending_interrupt_id is not None:
            phase = WorkspacePhase.APPROVAL
        elif job.result is not None:
            phase = (
                WorkspacePhase.COMPLETE if job.result.ready_candidate else WorkspacePhase.BLOCKED
            )
        else:
            phase = WorkspacePhase.ERROR
        workspace.record = workspace.record.model_copy(
            update={
                "phase": phase,
                "pending_interrupt_id": job.pending_interrupt_id,
                "error": workspace.record.error,
            }
        )

    def _record_runtime_events(self, workspace: HostedWorkspace) -> None:
        """Append an idempotent deterministic tool ledger without routine model prose."""
        runtime = workspace.runtime
        if runtime is None:
            return
        event_types = {event.event_type for event in workspace.record.events}
        job = runtime.job
        if job.inspection is not None and "POLICY_INSPECTION_COMPLETED" not in event_types:
            workspace.record = self._append_event(
                workspace.record,
                "POLICY_INSPECTION_COMPLETED",
                evidence_refs=(job.inspection.inspection_id,),
                payload={
                    "finding_count": len(job.inspection.findings),
                    "repair_eligibility": job.inspection.repair_eligibility.value,
                },
            )
        if job.selected_plan is not None and "REPAIR_PLAN_REGISTERED" not in event_types:
            workspace.record = self._append_event(
                workspace.record,
                "REPAIR_PLAN_REGISTERED",
                evidence_refs=(job.selected_plan.plan_id,),
                payload={
                    "candidate_ids": [candidate.id for candidate in job.selected_plan.candidates],
                    "approval_action_ids": list(job.selected_plan.approval_action_ids),
                },
            )
        if job.pending_interrupt_id is not None and "APPROVAL_INTERRUPT_CREATED" not in event_types:
            workspace.record = self._append_event(
                workspace.record,
                "APPROVAL_INTERRUPT_CREATED",
                evidence_refs=(job.pending_interrupt_id,),
                payload={"candidate_id": "normalize-root-v1"},
            )
        if job.result is not None and "DETERMINISTIC_WORKFLOW_COMPLETED" not in event_types:
            workspace.record = self._append_event(
                workspace.record,
                "DETERMINISTIC_WORKFLOW_COMPLETED",
                evidence_refs=(job.result.job_id,),
                payload={
                    "phase": workspace.record.phase.value,
                    "ready_candidate": workspace.ready_candidate,
                },
            )

    def get(self, workspace_id: str) -> HostedWorkspace | None:
        """Load a workspace and reconstruct its Strands/deterministic runtime after restart."""
        try:
            path = self._record_path(workspace_id)
        except HostedWorkspaceError:
            return None
        if not path.is_file():
            return None
        record = HostedWorkspaceRecord.model_validate_json(path.read_text(encoding="utf-8"))
        workspace = HostedWorkspace(record=record, root=path.parent)
        self._load_runtime(workspace)
        if workspace.runtime is not None:
            previous_phase = workspace.record.phase
            previous_event_count = len(workspace.record.events)
            self._sync_runtime(workspace)
            self._record_runtime_events(workspace)
            if (
                workspace.record.phase is not previous_phase
                or len(workspace.record.events) != previous_event_count
            ):
                self._persist(workspace)
        return workspace

    def decide(
        self,
        workspace: HostedWorkspace,
        *,
        interrupt_id: str,
        approved: bool,
        command_id: str,
    ) -> HostedWorkspace:
        """Apply one idempotent structured response to the exact native interrupt."""
        if _COMMAND_ID.fullmatch(command_id) is None:
            raise HostedWorkspaceError("The decision command identifier is invalid.")
        with self._lock:
            previous = workspace.record.processed_commands.get(command_id)
            expected_value = f"DECISION:{interrupt_id}:{'APPROVE' if approved else 'REJECT'}"
            if previous is not None and previous != expected_value:
                if previous == f"{expected_value}:COMPLETE":
                    return workspace
                raise HostedWorkspaceError("This command identifier was used for another action.")
            if workspace.runtime is None:
                raise HostedWorkspaceError("The deterministic job runtime is unavailable.")
            if workspace.runtime.job.result is not None:
                self._sync_runtime(workspace)
                return workspace
            if workspace.runtime.job.pending_interrupt_id != interrupt_id:
                raise HostedWorkspaceError(
                    "The approval response does not match this workspace's pending action."
                )
            processed = {**workspace.record.processed_commands, command_id: expected_value}
            workspace.record = workspace.record.model_copy(update={"processed_commands": processed})
            workspace.record = self._append_event(
                workspace.record,
                "STRUCTURED_DECISION_SUBMITTED",
                evidence_refs=(interrupt_id,),
                payload={"approved": approved, "candidate_id": "normalize-root-v1"},
            )
            self._persist(workspace)
            try:
                workspace.latest_result = workspace.runtime.resume(interrupt_id, approved=approved)
                workspace.workflow_result = workspace.runtime.complete(workspace.latest_result)
            except AgentWorkflowError:
                raise
            except Exception as error:
                workspace.record = workspace.record.model_copy(
                    update={"phase": WorkspacePhase.ERROR, "error": str(error)}
                )
                self._persist(workspace)
                return workspace
            processed = {
                **workspace.record.processed_commands,
                command_id: f"{expected_value}:COMPLETE",
            }
            workspace.record = workspace.record.model_copy(update={"processed_commands": processed})
            self._sync_runtime(workspace)
            self._record_runtime_events(workspace)
            self._persist(workspace)
            return workspace

    def answer_evidence_question(
        self, workspace: HostedWorkspace, category: str
    ) -> HostedWorkspace:
        """Answer a bounded question from recorded facts without storing conversational prose."""
        preflight = workspace.record.preflight
        if category == "measurements" and preflight.geometry is not None:
            dimensions = preflight.geometry.bounds.dimensions_m
            answer = EvidenceAnswer(
                category=category,
                title="Measured source dimensions",
                statements=(
                    (
                        f"The represented bounds are {dimensions[0]:.3f} x "
                        f"{dimensions[1]:.3f} x {dimensions[2]:.3f} m."
                    ),
                    (
                        f"The dominant extent is "
                        f"{preflight.geometry.dominant_dimension_axis}; ground relationship is "
                        f"{preflight.geometry.ground_relationship}."
                    ),
                ),
                evidence_refs=(preflight.preflight_id,),
                answered_at=datetime.now(UTC),
            )
        elif category == "materials":
            transparent = sum(material.alpha_mode != "OPAQUE" for material in preflight.materials)
            emissive = sum(
                any(value != 0.0 for value in material.emissive_factor)
                for material in preflight.materials
            )
            answer = EvidenceAnswer(
                category=category,
                title="Declared material metadata",
                statements=(
                    (
                        f"The GLB declares {len(preflight.materials)} materials; {transparent} "
                        f"use a non-opaque alpha mode and {emissive} declare a non-zero "
                        "emissive factor."
                    ),
                    "This is metadata evidence, not a visual judgment of appearance.",
                ),
                evidence_refs=(preflight.preflight_id,),
                answered_at=datetime.now(UTC),
            )
        elif category == "authorization":
            answer = EvidenceAnswer(
                category=category,
                title="Authorization boundary",
                statements=(
                    "Chat text cannot approve a repair.",
                    (
                        "Only the exact Approve or Reject control bound to the pending interrupt "
                        "can authorize the grouped physical normalization."
                    ),
                ),
                evidence_refs=(workspace.record.pending_interrupt_id or "no-pending-interrupt",),
                answered_at=datetime.now(UTC),
            )
        else:
            job = workspace.runtime.job if workspace.runtime is not None else None
            answer = EvidenceAnswer(
                category="result",
                title="Current deterministic result",
                statements=(
                    (
                        f"Verification state is {job.last_verification.state.value}."
                        if job and job.last_verification
                        else "Verification has not completed."
                    ),
                    (
                        "A contracted result package is ready."
                        if job and job.result
                        else "No result package is ready yet."
                    ),
                ),
                evidence_refs=((job.result.job_id,) if job and job.result else ()),
                answered_at=datetime.now(UTC),
            )
        workspace.record = workspace.record.model_copy(update={"last_answer": answer})
        workspace.record = self._append_event(
            workspace.record,
            "EVIDENCE_ANSWERED",
            evidence_refs=answer.evidence_refs,
            payload={"category": answer.category},
        )
        self._persist(workspace)
        return workspace
