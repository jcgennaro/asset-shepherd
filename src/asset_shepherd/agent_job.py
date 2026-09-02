"""Stateful, path-confined stages exposed to the Strands agent."""

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Final, Literal, Protocol, cast

import numpy as np
from PIL import Image, ImageStat, UnidentifiedImageError

from asset_shepherd.glb import load_glb, node_local_matrix
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentCandidateReassessment,
    AgentDisposition,
    AgentRepairAssessment,
    ApprovalCard,
    AssetIntentProvenance,
    CheckBasis,
    CheckStatus,
    ComponentRemovalPayload,
    ConversationTurnRecord,
    DecisionRecord,
    Decisions,
    DecisionSource,
    DecisionValue,
    DegenerateGeometryPayload,
    InspectionResult,
    JobResult,
    JobState,
    Matrix4,
    MeshSimplificationPayload,
    NormalizationPayload,
    PivotAnchorInventory,
    PlanSelection,
    ProfilePolicyProvenance,
    ProjectProfile,
    ProposalDisposition,
    ProposalLane,
    ProposalResponse,
    Provenance,
    RepairKind,
    RepairPlan,
    VerificationCheck,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.pivot import inspect_pivot_anchors as measure_pivot_anchors
from asset_shepherd.planner import plan_agent_repairs, plan_repairs
from asset_shepherd.profile_policy import (
    build_profile_policy_provenance,
    validate_profile_policy_provenance,
)
from asset_shepherd.repair import RepairOutcome, apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.web_evidence_renderer import (
    WebEvidenceRendererError,
    render_model_views,
)
from asset_shepherd.workflow import (
    build_blocked_verification,
    build_provenance,
    package_artifacts,
    render_final_report,
)


class AgentWorkflowError(RuntimeError):
    """Raised when the agent violates the deterministic stage contract."""


class VerificationFunction(Protocol):
    """Callable contract used to inject one deterministic verification implementation."""

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
        """Return deterministic verification for one on-disk candidate."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")


GLTF_SOURCE_VIEW_CONTRACT: Final[dict[str, object]] = {
    "schema_version": 1,
    "render_contract_version": 6,
    "render_backend": "model-viewer 4.3.1 through headless Chromium",
    "projection": "fixed 24-degree perspective with standardized framing",
    "source_coordinate_system": "glTF right-handed",
    "source_up": "+Y",
    "source_forward": "+Z",
    "source_right": "-X",
    "views": {
        "front.png": "camera at source +Z; a correctly facing front looks toward the camera",
        "right.png": "camera at source -X; the asset's right side looks toward the camera",
        "back.png": "camera at source -Z; the back looks toward the camera",
        "left.png": "camera at source +X; the asset's left side looks toward the camera",
    },
    "evidence_validation": {
        "decodable_png": True,
        "minimum_foreground_fraction": 0.005,
        "minimum_projected_span_fraction": 0.08,
        "maximum_foreground_fraction": 0.8,
        "requires_clear_frame_margin": True,
    },
}

_BLENDER_SOURCE_VIEW_CONTRACT: Final[dict[str, object]] = {
    **GLTF_SOURCE_VIEW_CONTRACT,
    "render_contract_version": 5,
    "render_backend": "Blender compatibility fallback",
    "projection": "orthographic",
}


def _matrix_contract(matrix: np.ndarray) -> Matrix4:
    """Convert one finite NumPy matrix to the immutable public matrix shape."""
    return (
        (float(matrix[0, 0]), float(matrix[0, 1]), float(matrix[0, 2]), float(matrix[0, 3])),
        (float(matrix[1, 0]), float(matrix[1, 1]), float(matrix[1, 2]), float(matrix[1, 3])),
        (float(matrix[2, 0]), float(matrix[2, 1]), float(matrix[2, 2]), float(matrix[2, 3])),
        (float(matrix[3, 0]), float(matrix[3, 1]), float(matrix[3, 2]), float(matrix[3, 3])),
    )


@dataclass
class AgentJob:
    """One local job whose mutation boundary is its configured output directory."""

    source: Path
    profile_path: Path
    output_dir: Path
    profile_policy: ProfilePolicyProvenance | None = None
    asset_intent: AssetIntentProvenance | None = None
    agent_orchestrated: bool = False
    max_turns: int = 5
    clock: Callable[[], datetime] = _utc_now
    verification_function: VerificationFunction = verify_repair
    profile: ProjectProfile = field(init=False)
    started_at: datetime | None = field(default=None, init=False)
    inspection: InspectionResult | None = field(default=None, init=False)
    full_plan: RepairPlan | None = field(default=None, init=False)
    selection: PlanSelection | None = field(default=None, init=False)
    selected_plan: RepairPlan | None = field(default=None, init=False)
    decisions: Decisions | None = field(default=None, init=False)
    outcome: RepairOutcome | None = field(default=None, init=False)
    provenance: Provenance | None = field(default=None, init=False)
    last_verification: VerificationResult | None = field(default=None, init=False)
    result: JobResult | None = field(default=None, init=False)
    pending_interrupt_id: str | None = field(default=None, init=False)
    correction_attempts: int = field(default=0, init=False)
    agent_assessment: AgentRepairAssessment | None = field(default=None, init=False)
    candidate_reassessment: AgentCandidateReassessment | None = field(default=None, init=False)
    turn_index: int = field(default=0, init=False)
    prior_turns: tuple[ConversationTurnRecord, ...] = field(default=(), init=False)
    accepted: bool = field(default=False, init=False)
    original_source: Path = field(init=False)

    def __post_init__(self) -> None:
        """Resolve trusted caller paths before exposing path-free agent tools."""
        self.source = self.source.resolve(strict=True)
        self.original_source = self.source
        self.profile_path = self.profile_path.resolve(strict=True)
        self.output_dir = self.output_dir.resolve(strict=False)
        if self.source.suffix.lower() != ".glb":
            raise AgentWorkflowError("Agent jobs accept exactly one .glb source")
        if self.output_dir == self.source:
            raise AgentWorkflowError("Agent output directory cannot be the source file")
        if not 1 <= self.max_turns <= 50:
            raise AgentWorkflowError("Agent turn limit must be between 1 and 50")
        self.profile = ProjectProfile.model_validate_json(
            self.profile_path.read_text(encoding="utf-8")
        )
        if self.profile_policy is None:
            self.profile_policy = build_profile_policy_provenance(self.profile)
        else:
            validate_profile_policy_provenance(self.profile, self.profile_policy)
        self._restore_runtime_state()

    @property
    def runtime_state_path(self) -> Path:
        """Return private resumable state kept outside the contracted artifact directory."""
        return self.output_dir.parent / "runtime_state.json"

    @property
    def pivot_anchor_inventory_path(self) -> Path:
        """Return the source-bound geometry landmark inventory for this turn."""
        return self.output_dir / "pivot_anchors.json"

    @property
    def agent_assessment_path(self) -> Path:
        """Return private model judgment kept outside the contracted evidence ZIP."""
        return self.output_dir.parent / "agent_assessment.json"

    @property
    def candidate_reassessment_path(self) -> Path:
        """Return private post-action model judgment kept outside the evidence ZIP."""
        return self.output_dir.parent / "candidate_reassessment.json"

    def _persist_runtime_state(self) -> None:
        """Atomically persist the minimum deterministic state needed after a restart."""
        state = {
            "schema_version": 1,
            "source_sha256": (
                self.inspection.package.file_sha256 if self.inspection is not None else None
            ),
            "started_at": self.started_at.isoformat() if self.started_at is not None else None,
            "pending_interrupt_id": self.pending_interrupt_id,
            "correction_attempts": self.correction_attempts,
            "agent_orchestrated": self.agent_orchestrated,
            "max_turns": self.max_turns,
            "turn_index": self.turn_index,
            "working_source": str(self.source) if self.turn_index else None,
            "prior_turns": [turn.model_dump(mode="json") for turn in self.prior_turns],
            "accepted": self.accepted,
            "phase": (
                "complete"
                if self.result is not None
                else "verified"
                if self.last_verification is not None
                else "executed"
                if self.outcome is not None
                else "planned"
                if self.selected_plan is not None
                else "inspected"
                if self.inspection is not None
                else "created"
            ),
        }
        path = self.runtime_state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        _write_json(temporary, state)
        temporary.replace(path)

    def _restore_runtime_state(self) -> None:
        """Restore typed deterministic state from private state and contracted artifacts."""
        state_path = self.runtime_state_path
        if not state_path.is_file():
            return
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != 1:
            raise AgentWorkflowError("Unsupported agent runtime-state version")
        started_at = state.get("started_at")
        if started_at is not None:
            self.started_at = datetime.fromisoformat(str(started_at))
        pending_interrupt_id = state.get("pending_interrupt_id")
        self.pending_interrupt_id = (
            str(pending_interrupt_id) if pending_interrupt_id is not None else None
        )
        self.correction_attempts = int(state.get("correction_attempts", 0))
        persisted_max_turns = int(state.get("max_turns", self.max_turns))
        if not 1 <= persisted_max_turns <= 50:
            raise AgentWorkflowError("Persisted agent turn limit is invalid")
        self.max_turns = persisted_max_turns
        self.turn_index = int(state.get("turn_index", 0))
        self.prior_turns = tuple(
            ConversationTurnRecord.model_validate_json(json.dumps(turn))
            for turn in state.get("prior_turns", [])
        )
        if self.turn_index != len(self.prior_turns) or self.turn_index >= self.max_turns:
            raise AgentWorkflowError("Persisted conversation turn chain is invalid")
        self.accepted = bool(state.get("accepted", False))
        working_source = state.get("working_source")
        if working_source is not None:
            restored_source = Path(str(working_source)).resolve(strict=True)
            turn_root = (self.output_dir.parent / "turns").resolve(strict=False)
            original_source = self.original_source.resolve(strict=True)
            if restored_source != original_source:
                try:
                    restored_source.relative_to(turn_root)
                except ValueError as error:
                    raise AgentWorkflowError(
                        "Persisted working source is outside the immutable iteration history"
                    ) from error
            if restored_source.suffix.lower() != ".glb":
                raise AgentWorkflowError("Persisted working source is not a GLB")
            self.source = restored_source
        persisted_agent_mode = bool(state.get("agent_orchestrated", False))
        if persisted_agent_mode != self.agent_orchestrated:
            raise AgentWorkflowError("Persisted planning authority does not match this runtime")
        inspection_path = self.output_dir / "inspection.json"
        plan_path = self.output_dir / "repair_plan.json"
        decisions_path = self.output_dir / "decisions.json"
        provenance_path = self.output_dir / "provenance.json"
        verification_path = self.output_dir / "verification.json"
        result_path = self.output_dir / "job_result.json"
        if self.agent_assessment_path.is_file():
            self.agent_assessment = AgentRepairAssessment.model_validate_json(
                self.agent_assessment_path.read_text(encoding="utf-8")
            )
        if self.candidate_reassessment_path.is_file():
            self.candidate_reassessment = AgentCandidateReassessment.model_validate_json(
                self.candidate_reassessment_path.read_text(encoding="utf-8")
            )
        if inspection_path.is_file():
            self.inspection = InspectionResult.model_validate_json(
                inspection_path.read_text(encoding="utf-8")
            )
            expected_hash = state.get("source_sha256")
            if expected_hash is not None and self.inspection.package.file_sha256 != expected_hash:
                raise AgentWorkflowError("Persisted source identity does not match inspection")
        if plan_path.is_file():
            self.selected_plan = RepairPlan.model_validate_json(
                plan_path.read_text(encoding="utf-8")
            )
            self.full_plan = self.selected_plan
            self.selection = PlanSelection(
                plan_id=self.selected_plan.plan_id,
                candidate_ids=tuple(candidate.id for candidate in self.selected_plan.candidates),
            )
        if decisions_path.is_file():
            self.decisions = Decisions.model_validate_json(
                decisions_path.read_text(encoding="utf-8")
            )
        if provenance_path.is_file():
            self.provenance = Provenance.model_validate_json(
                provenance_path.read_text(encoding="utf-8")
            )
        if self.decisions is not None and self.provenance is not None:
            rejected = tuple(
                record.candidate_id
                for record in self.decisions.records
                if record.decision is DecisionValue.REJECTED
            )
            executed = tuple(action.candidate_id for action in self.provenance.executed_actions)
            candidate = self.output_dir / "candidate.glb"
            repaired = self.output_dir / "repaired.glb"
            if self.provenance.output_sha256 is not None and (
                candidate.is_file() or repaired.is_file()
            ):
                self.outcome = RepairOutcome(
                    source_sha256=self.provenance.source_sha256,
                    output_sha256=self.provenance.output_sha256,
                    executed_action_ids=executed,
                    rejected_action_ids=rejected,
                )
        if verification_path.is_file():
            self.last_verification = VerificationResult.model_validate_json(
                verification_path.read_text(encoding="utf-8")
            )
        if result_path.is_file():
            self.result = JobResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        if (
            self.outcome is not None
            and self.pending_interrupt_id is not None
            and self.candidate_reassessment is None
            and self.last_verification is None
        ):
            # The approved action was durably executed, but the provider stopped before its
            # post-action assessment. That approval is consumed; expose bounded recovery instead
            # of restoring the stale button and executing the same repair again.
            self.pending_interrupt_id = None
            self._persist_runtime_state()

    def set_pending_interrupt(self, interrupt_id: str | None) -> None:
        """Persist the exact native interrupt identity or its durable resolution."""
        self.pending_interrupt_id = interrupt_id
        self._persist_runtime_state()

    def request_plan_revision(
        self, responses: tuple[ProposalResponse, ...]
    ) -> tuple[ProposalResponse, ...]:
        """Archive a pending agent plan and reopen planning without mutating the GLB."""
        if not self.agent_orchestrated:
            raise AgentWorkflowError("Plan revision requires agent-orchestrated mode")
        if self.selected_plan is None or self.agent_assessment is None:
            raise AgentWorkflowError("A pending agent plan is required for revision")
        inspection = self.inspection
        if inspection is None:
            raise AgentWorkflowError("Plan revision requires the source inspection")
        if self.pending_interrupt_id is None:
            raise AgentWorkflowError("Plan revision requires the exact pending interrupt")
        if self.outcome is not None:
            raise AgentWorkflowError("An executed plan cannot be revised in place")
        if not responses or all(
            response.disposition is ProposalDisposition.ACCEPT for response in responses
        ):
            raise AgentWorkflowError("Plan revision requires a rejection or comment")

        active_lanes: set[ProposalLane] = {ProposalLane.GENERAL}
        for candidate in self.selected_plan.candidates:
            if candidate.kind is RepairKind.NORMALIZATION_TRANSFORM:
                active_lanes.add(ProposalLane.SIZE_AND_POSE)
            elif candidate.kind in {
                RepairKind.WELD_IDENTICAL_VERTICES,
                RepairKind.CLEAN_DEGENERATE_GEOMETRY,
                RepairKind.REMOVE_DISCONNECTED_COMPONENTS,
                RepairKind.SIMPLIFY_MESH,
            }:
                active_lanes.add(ProposalLane.TOPOLOGY)
            elif candidate.kind in {RepairKind.RENAME_MESH, RepairKind.RENAME_NODE}:
                active_lanes.add(ProposalLane.DISPLAY_NAMES)
        active_removed_component_ids = {
            component_id
            for candidate in self.selected_plan.candidates
            if isinstance(candidate.payload, ComponentRemovalPayload)
            for primitive in candidate.payload.primitives
            for component_id in primitive.removed_component_ids
        }
        active_component_ids = set(active_removed_component_ids)
        if inspection.diagnostics is not None:
            safe_review_component_ids = {
                component.component_id
                for primitive in inspection.diagnostics.primitives
                if primitive.component_removal_safe and len(primitive.disconnected_components) > 1
                for component in primitive.disconnected_components
            }
            if safe_review_component_ids:
                active_lanes.add(ProposalLane.TOPOLOGY)
                active_component_ids.update(safe_review_component_ids)
        unknown_lanes = {response.lane for response in responses} - active_lanes
        if unknown_lanes:
            raise AgentWorkflowError(
                f"Plan feedback references inactive proposal lanes: {sorted(unknown_lanes)}"
            )
        unknown_component_ids = {
            response.component_id for response in responses if response.component_id is not None
        } - active_component_ids
        if unknown_component_ids:
            raise AgentWorkflowError(
                f"Plan feedback references inactive components: {sorted(unknown_component_ids)}"
            )

        revision_root = self.output_dir.parent / "plan_revisions"
        revision_index = (
            len(tuple(revision_root.glob(f"turn-{self.turn_index:03d}-revision-*"))) + 1
        )
        plan_id = self.selected_plan.plan_id
        plan_path = self.output_dir / "repair_plan.json"
        if not plan_path.is_file() or not self.agent_assessment_path.is_file():
            raise AgentWorkflowError("The pending plan is missing its durable evidence")
        archive = revision_root / (f"turn-{self.turn_index:03d}-revision-{revision_index:03d}")
        archive.mkdir(parents=True, exist_ok=False)
        shutil.move(str(plan_path), str(archive / "repair_plan.json"))
        shutil.move(str(self.agent_assessment_path), str(archive / "agent_assessment.json"))
        _write_json(
            archive / "revision_request.json",
            {
                "schema_version": 1,
                "plan_id": plan_id,
                "turn_index": self.turn_index,
                "responses": [response.model_dump(mode="json") for response in responses],
                "recorded_at": self.clock().isoformat(),
            },
        )
        self.full_plan = None
        self.selection = None
        self.selected_plan = None
        self.agent_assessment = None
        self.pending_interrupt_id = None
        self._persist_runtime_state()
        return responses

    @property
    def turns_remaining(self) -> int:
        """Return how many additional user-requested repair turns remain."""
        return max(0, self.max_turns - self.turn_index - 1)

    def begin_next_turn(
        self,
        feedback: str,
        *,
        continuation_source: Literal["INPUT", "CANDIDATE"] = "CANDIDATE",
    ) -> ConversationTurnRecord:
        """Archive one completed turn and promote the selected immutable iteration."""
        feedback = feedback.strip()
        if not self.agent_orchestrated:
            raise AgentWorkflowError("Multi-turn repair requires agent-orchestrated mode")
        if self.accepted:
            raise AgentWorkflowError("This conversation is already accepted")
        if not feedback:
            raise AgentWorkflowError("Explain what still needs attention")
        if len(feedback) > 1000:
            raise AgentWorkflowError("Repair feedback must be 1,000 characters or fewer")
        if self.turns_remaining <= 0:
            raise AgentWorkflowError("This conversation has reached its configured turn limit")
        if (
            self.result is None
            or self.provenance is None
            or self.last_verification is None
            or self.inspection is None
            or self.selected_plan is None
        ):
            raise AgentWorkflowError("The current turn must finish before another can begin")
        if continuation_source not in {"INPUT", "CANDIDATE"}:
            raise AgentWorkflowError("Choose the current iteration or its candidate")
        current_source = self.source.resolve(strict=True)
        repaired = self.output_dir / "repaired.glb"
        failed_candidate = self.output_dir / "candidate.glb"
        candidate_source = repaired if repaired.is_file() else failed_candidate
        if continuation_source == "CANDIDATE" and not candidate_source.is_file():
            raise AgentWorkflowError("The completed turn has no candidate to refine")
        result_zip = self.output_dir / "result.zip"
        if not result_zip.is_file() or self.provenance.output_sha256 is None:
            raise AgentWorkflowError("The completed turn is missing its evidence package")
        record = ConversationTurnRecord(
            turn_index=self.turn_index,
            source_sha256=self.inspection.package.file_sha256,
            output_sha256=self.provenance.output_sha256,
            plan_id=self.selected_plan.plan_id,
            agent_assessment_id=(
                self.agent_assessment.assessment_id if self.agent_assessment is not None else None
            ),
            candidate_reassessment_id=(
                self.candidate_reassessment.reassessment_id
                if self.candidate_reassessment is not None
                else None
            ),
            verification_state=self.last_verification.state,
            result_zip_sha256=sha256(result_zip.read_bytes()).hexdigest(),
            continuation_feedback=feedback,
            continuation_source=continuation_source,
            next_source_sha256=(
                self.provenance.output_sha256
                if continuation_source == "CANDIDATE"
                else self.inspection.package.file_sha256
            ),
        )
        turn_root = self.output_dir.parent / "turns" / f"turn-{self.turn_index:03d}"
        if turn_root.exists():
            raise AgentWorkflowError("Conversation turn archive already exists")
        turn_root.parent.mkdir(parents=True, exist_ok=True)
        turn_root.mkdir()
        archive_output = turn_root / "output"
        shutil.move(str(self.output_dir), str(archive_output))
        for private_path in (self.agent_assessment_path, self.candidate_reassessment_path):
            if private_path.is_file():
                shutil.move(str(private_path), str(turn_root / private_path.name))
        evidence_root = self.output_dir.parent / "agent_evidence"
        if evidence_root.is_dir():
            shutil.move(str(evidence_root), str(turn_root / "agent_evidence"))
        next_source = (
            archive_output / candidate_source.name
            if continuation_source == "CANDIDATE"
            else current_source
        )
        self.prior_turns = (*self.prior_turns, record)
        self.turn_index += 1
        self.source = next_source.resolve(strict=True)
        self.started_at = None
        self.inspection = None
        self.full_plan = None
        self.selection = None
        self.selected_plan = None
        self.decisions = None
        self.outcome = None
        self.provenance = None
        self.last_verification = None
        self.result = None
        self.pending_interrupt_id = None
        self.correction_attempts = 0
        self.agent_assessment = None
        self.candidate_reassessment = None
        manifest = {
            "schema_version": 1,
            "max_turns": self.max_turns,
            "current_turn_index": self.turn_index,
            "turns": [turn.model_dump(mode="json") for turn in self.prior_turns],
        }
        _write_json(self.output_dir.parent / "conversation.json", manifest)
        self._persist_runtime_state()
        return record

    def record_user_acceptance(self) -> None:
        """Durably close the current conversation after the user accepts its result."""
        if self.result is None:
            raise AgentWorkflowError("A completed turn is required before acceptance")
        self.accepted = True
        payload = {
            "schema_version": 1,
            "max_turns": self.max_turns,
            "current_turn_index": self.turn_index,
            "accepted": True,
            "accepted_at": self.clock().isoformat(),
            "turns": [turn.model_dump(mode="json") for turn in self.prior_turns],
            "current_result": self.result.model_dump(mode="json"),
        }
        _write_json(self.output_dir.parent / "conversation.json", payload)
        self._persist_runtime_state()

    @property
    def candidate_path(self) -> Path:
        """Return the only mutable GLB candidate path inside this job."""
        return self.output_dir / "candidate.glb"

    @property
    def deterministic_completion_available(self) -> bool:
        """Return whether invariant verification can finish this already-decided turn.

        A provider may end its response immediately after recording the required visual
        reassessment instead of making the final ``verify_and_package`` tool call. Verification
        and packaging do not choose or mutate a repair; they enforce the mandatory invariant
        boundary over the candidate the agent already chose and executed. This predicate keeps
        that recovery narrow and fail-closed.

        """
        if self.result is not None or self.pending_interrupt_id is not None:
            return False
        if self.inspection is None or self.selected_plan is None or self.started_at is None:
            return False
        if self.selected_plan.blocked:
            return True
        if self.decisions is None or self.outcome is None or self.provenance is None:
            return False
        visually_consequential_kinds = {
            RepairKind.NORMALIZATION_TRANSFORM,
            RepairKind.WELD_IDENTICAL_VERTICES,
            RepairKind.CLEAN_DEGENERATE_GEOMETRY,
            RepairKind.REMOVE_DISCONNECTED_COMPONENTS,
            RepairKind.SIMPLIFY_MESH,
        }
        visually_consequential_action_ids = {
            candidate.id
            for candidate in self.selected_plan.candidates
            if candidate.kind in visually_consequential_kinds
        }
        requires_visual_reassessment = bool(
            visually_consequential_action_ids.intersection(self.outcome.executed_action_ids)
        )
        return not requires_visual_reassessment or self.candidate_reassessment is not None

    def _require_output_path(self, path: Path) -> None:
        try:
            path.resolve(strict=False).relative_to(self.output_dir)
        except ValueError as error:
            raise AgentWorkflowError(
                "Agent tool attempted to write outside its job directory"
            ) from error

    def inspect(self) -> InspectionResult:
        """Inspect once and persist the structured facts artifact."""
        if self.inspection is not None:
            return self.inspection
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.started_at = self.clock()
        inspection = inspect_asset(self.source, self.profile, policy=self.profile_policy)
        if self.agent_orchestrated:
            semantic_codes = {"HEIGHT_OUT_OF_RANGE", "ORIENTATION_NOT_Y_UP", "NOT_GROUNDED"}
            inspection = inspection.model_copy(
                update={
                    "findings": tuple(
                        finding
                        for finding in inspection.findings
                        if finding.code not in semantic_codes
                    )
                }
            )
        self.inspection = inspection
        inspection_path = self.output_dir / "inspection.json"
        self._require_output_path(inspection_path)
        _write_json(inspection_path, self.inspection.model_dump(mode="json"))
        self._persist_runtime_state()
        return self.inspection

    def objective_observations(self) -> dict[str, object]:
        """Return measurements without deterministic target-dependent conclusions."""
        inspection = self.inspect()
        pivot_observation: dict[str, object] | None = None
        if inspection.geometry is not None and inspection.diagnostics is not None:
            bounds = inspection.geometry.bounds
            bounds_center = tuple(
                (bounds.minimum_m[index] + bounds.maximum_m[index]) / 2.0 for index in range(3)
            )
            pivot_observation = {
                "asset_origin_m": (0.0, 0.0, 0.0),
                "bounds_center_m": bounds_center,
                "footprint_center_bottom_m": inspection.diagnostics.bounds_ground_center_m,
                "root_world_origins_m": inspection.diagnostics.root_world_origins_m,
                "interpretation": (
                    "Ground contact and pivot placement are separate target conditions. These "
                    "coordinates are measurements only; intended placement determines the anchor."
                ),
            }
        return {
            "source_filename": inspection.source_filename,
            "package": inspection.package.model_dump(mode="json"),
            "geometry": (
                inspection.geometry.model_dump(mode="json")
                if inspection.geometry is not None
                else None
            ),
            "transforms": (
                inspection.transforms.model_dump(mode="json")
                if inspection.transforms is not None
                else None
            ),
            "naming": (
                inspection.naming.model_dump(mode="json") if inspection.naming is not None else None
            ),
            "resources": (
                inspection.resources.model_dump(mode="json")
                if inspection.resources is not None
                else None
            ),
            "repair_eligibility": inspection.repair_eligibility.value,
            "source_diagnostics": (
                inspection.diagnostics.model_dump(mode="json")
                if inspection.diagnostics is not None
                else None
            ),
            "pivot_observation": pivot_observation,
            "non_semantic_findings": [
                finding.model_dump(mode="json") for finding in inspection.findings
            ],
            "interpretation_boundary": (
                "Dimensions, dominant axis, and ground relationship are observations only. "
                "They do not establish semantic height or justify rotation. Boundary edges, "
                "connected components, coincident positions, and cache estimates are diagnostic "
                "facts, not automatic defects or repair authorization."
            ),
        }

    def inspect_pivot_anchors(self) -> PivotAnchorInventory:
        """Measure a bounded set of selectable origin candidates for the current source."""
        inspection = self.inspect()
        try:
            inventory = measure_pivot_anchors(self.source, inspection)
        except (OSError, ValueError, IndexError, TypeError) as error:
            raise AgentWorkflowError(f"Pivot anchor sensing failed: {error}") from error
        self._require_output_path(self.pivot_anchor_inventory_path)
        _write_json(
            self.pivot_anchor_inventory_path,
            inventory.model_dump(mode="json"),
        )
        return inventory

    def _trusted_existing_normalization_root(self) -> tuple[int, Matrix4] | None:
        """Return a prior Asset Shepherd root only when the immediate lineage proves it."""
        if self.turn_index <= 0 or not self.prior_turns:
            return None
        current_hash = sha256(self.source.read_bytes()).hexdigest()
        prior_record = self.prior_turns[-1]
        if prior_record.output_sha256 != current_hash:
            return None
        prior_output = (
            self.output_dir.parent / "turns" / f"turn-{self.turn_index - 1:03d}" / "output"
        )
        plan_path = prior_output / "repair_plan.json"
        provenance_path = prior_output / "provenance.json"
        if not plan_path.is_file() or not provenance_path.is_file():
            return None
        try:
            prior_plan = RepairPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
            prior_provenance = Provenance.model_validate_json(
                provenance_path.read_text(encoding="utf-8")
            )
            if prior_provenance.output_sha256 != current_hash:
                return None
            executed = {action.candidate_id for action in prior_provenance.executed_actions}
            normalization = next(
                (
                    candidate.payload
                    for candidate in prior_plan.candidates
                    if candidate.id in executed
                    and isinstance(candidate.payload, NormalizationPayload)
                ),
                None,
            )
            if normalization is None:
                return None
            gltf = load_glb(self.source)
            if not gltf.scenes or not gltf.nodes:
                return None
            if normalization.application_mode == "COMPOSE_EXISTING_ROOT":
                root_index = normalization.existing_root_index
                expected_matrix = normalization.existing_root_after_matrix
            else:
                root_index = len(gltf.nodes) - 1
                expected_matrix = normalization.proposed_matrix
            if (
                root_index is None
                or expected_matrix is None
                or not 0 <= root_index < len(gltf.nodes)
            ):
                return None
            scene_index = gltf.scene or 0
            if not 0 <= scene_index < len(gltf.scenes):
                return None
            roots = tuple(gltf.scenes[scene_index].nodes or ())
            root = gltf.nodes[root_index]
            if (
                roots != (root_index,)
                or not (root.name or "").startswith("AssetShepherdNormalization")
                or root.mesh is not None
                or root.camera is not None
                or root.skin is not None
                or not root.children
            ):
                return None
            current_matrix = node_local_matrix(root)
            if not np.allclose(
                current_matrix,
                np.asarray(expected_matrix, dtype=np.float64),
                rtol=0.0,
                atol=1e-12,
            ):
                return None
            return root_index, _matrix_contract(current_matrix)
        except (OSError, ValueError, TypeError, IndexError):
            return None

    def _render_asset_views(
        self,
        asset: Path,
        view_root: Path,
        *,
        reference_asset: Path | None = None,
    ) -> tuple[Path, ...]:
        """Render one trusted job asset into four standardized local views."""
        renderer = os.environ.get("ASSET_SHEPHERD_EVIDENCE_RENDERER", "web").strip().lower()
        if renderer not in {"web", "blender"}:
            raise AgentWorkflowError("ASSET_SHEPHERD_EVIDENCE_RENDERER must be 'web' or 'blender'")
        render_contract = (
            GLTF_SOURCE_VIEW_CONTRACT if renderer == "web" else _BLENDER_SOURCE_VIEW_CONTRACT
        )
        names = ("front.png", "right.png", "back.png", "left.png")
        existing = tuple(view_root / name for name in names)
        masks = tuple(view_root / name.replace(".png", ".mask.png") for name in names)
        contract_path = view_root / "view_contract.json"
        cached_evidence_error: AgentWorkflowError | None = None
        if all(path.is_file() for path in (*existing, *masks)) and contract_path.is_file():
            try:
                if json.loads(contract_path.read_text(encoding="utf-8")) == render_contract:
                    self.validate_render_evidence(
                        view_root, existing, render_contract=render_contract
                    )
                    return existing
            except AgentWorkflowError as error:
                cached_evidence_error = error
            except (OSError, json.JSONDecodeError):
                pass
        view_root.mkdir(parents=True, exist_ok=True)
        if renderer == "web":
            try:
                rendered = render_model_views(
                    asset,
                    view_root,
                    reference_asset=reference_asset,
                    resolution=512,
                )
            except WebEvidenceRendererError as error:
                if cached_evidence_error is not None:
                    raise cached_evidence_error from error
                raise AgentWorkflowError(f"Standardized visual sensing failed: {error}") from error
            self.validate_render_evidence(view_root, rendered, render_contract=render_contract)
            _write_json(contract_path, render_contract)
            return rendered
        configured = shutil.which("blender")
        blender = (
            Path(configured)
            if configured is not None
            else Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
        )
        if not blender.is_file():
            if cached_evidence_error is not None:
                raise cached_evidence_error
            raise AgentWorkflowError(
                "Standardized visual sensing is unavailable: Blender not found"
            )
        script = (
            Path(__file__).resolve().parents[2] / "validation" / "blender" / "render_turntable.py"
        )
        if not script.is_file():
            raise AgentWorkflowError("Standardized visual sensing script is unavailable")
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            "--python",
            str(script),
            "--",
            "--asset",
            str(asset),
            "--output-dir",
            str(view_root),
            "--resolution",
            "512",
        ]
        if reference_asset is not None:
            command.extend(["--reference-asset", str(reference_asset)])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0 or not all(path.is_file() for path in (*existing, *masks)):
            detail = completed.stderr.strip().splitlines()[-1:] or ["unknown Blender error"]
            raise AgentWorkflowError(f"Standardized visual sensing failed: {detail[0]}")
        self.validate_render_evidence(view_root, existing, render_contract=render_contract)
        _write_json(contract_path, render_contract)
        return existing

    def validate_render_evidence(
        self,
        view_root: Path,
        views: tuple[Path, ...],
        *,
        render_contract: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Reject undecodable, blank, clipped, or ineffectively framed render evidence."""
        active_contract = render_contract or GLTF_SOURCE_VIEW_CONTRACT
        metrics: dict[str, object] = {
            "schema_version": 1,
            "render_contract_version": active_contract["render_contract_version"],
            "render_backend": active_contract.get("render_backend", "unknown"),
            "views": {},
        }
        view_metrics: dict[str, object] = {}
        for path in views:
            mask_path = view_root / path.name.replace(".png", ".mask.png")
            try:
                with Image.open(path) as opened:
                    if opened.format != "PNG":
                        raise AgentWorkflowError(
                            f"Standardized visual sensing rejected {path.name}: not a PNG"
                        )
                    opened.load()
                    width, height = opened.size
                    rgb = opened.convert("RGB")
                with Image.open(mask_path) as opened_mask:
                    if opened_mask.format != "PNG" or opened_mask.size != (width, height):
                        raise AgentWorkflowError(
                            f"Standardized visual sensing rejected {path.name}: invalid object mask"
                        )
                    opened_mask.load()
                    mask = opened_mask.convert("L")
            except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as error:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: undecodable evidence"
                ) from error
            if width < 128 or height < 128:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: resolution is too small"
                )
            extrema = ImageStat.Stat(rgb).extrema
            if not any(high - low >= 4 for low, high in extrema):
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: image is visually blank"
                )
            mask_pixels = np.asarray(mask, dtype=np.uint8)
            foreground = mask_pixels >= 128
            foreground_pixels = int(np.count_nonzero(foreground))
            foreground_fraction = foreground_pixels / float(width * height)
            foreground_y, foreground_x = np.nonzero(foreground)
            if foreground_pixels == 0 or foreground_fraction < 0.005:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: asset is not visible"
                )
            if foreground_fraction > 0.8:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: asset fills the frame"
                )
            left = int(foreground_x.min())
            top = int(foreground_y.min())
            right = int(foreground_x.max()) + 1
            bottom = int(foreground_y.max()) + 1
            span_fraction = max((right - left) / width, (bottom - top) / height)
            if span_fraction < 0.08:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: asset is too small"
                )
            if left <= 0 or top <= 0 or right >= width or bottom >= height:
                raise AgentWorkflowError(
                    f"Standardized visual sensing rejected {path.name}: asset is clipped"
                )
            margin_fraction = min(left, top, width - right, height - bottom) / max(width, height)
            view_metrics[path.name] = {
                "width": width,
                "height": height,
                "image_sha256": sha256(path.read_bytes()).hexdigest(),
                "mask_sha256": sha256(mask_path.read_bytes()).hexdigest(),
                "foreground_fraction": foreground_fraction,
                "projected_span_fraction": span_fraction,
                "minimum_frame_margin_fraction": margin_fraction,
            }
        metrics["views"] = view_metrics
        _write_json(view_root / "render_evidence.json", metrics)
        return metrics

    def render_evidence_metrics(self, paths: tuple[Path, ...]) -> dict[str, object]:
        """Return freshly validated quality metrics for a standardized render set."""
        if not paths:
            raise AgentWorkflowError("No standardized render evidence was provided")
        contract: dict[str, object] | None = None
        contract_path = paths[0].parent / "view_contract.json"
        try:
            decoded = cast(object, json.loads(contract_path.read_text(encoding="utf-8")))
            if isinstance(decoded, dict):
                decoded_mapping = cast(dict[object, object], decoded)
                if all(isinstance(key, str) for key in decoded_mapping):
                    contract = {cast(str, key): value for key, value in decoded_mapping.items()}
        except (OSError, json.JSONDecodeError):
            pass
        return self.validate_render_evidence(paths[0].parent, paths, render_contract=contract)

    def render_source_views(self) -> tuple[Path, ...]:
        """Render four standardized model-consumable source views."""
        if self.inspection is None:
            raise AgentWorkflowError("Inspection must run before visual sensing")
        return self._render_asset_views(
            self.source,
            self.output_dir.parent / "agent_evidence" / "source_views",
        )

    def render_candidate_views(self) -> tuple[Path, ...]:
        """Render the executed candidate for model-visible before/after reassessment."""
        if self.outcome is None or not self.outcome.executed_action_ids:
            raise AgentWorkflowError("Candidate views require at least one executed action")
        if not self.candidate_path.is_file():
            raise AgentWorkflowError("Executed candidate is unavailable for visual sensing")
        return self._render_asset_views(
            self.candidate_path,
            self.output_dir.parent / "agent_evidence" / "candidate_views",
        )

    def render_candidate_comparison_views(self) -> tuple[Path, ...]:
        """Render source and candidate together at unchanged relative scale."""
        if self.outcome is None or not self.outcome.executed_action_ids:
            raise AgentWorkflowError("Comparison views require an executed candidate")
        if not self.candidate_path.is_file():
            raise AgentWorkflowError("Executed candidate is unavailable for visual sensing")
        return self._render_asset_views(
            self.candidate_path,
            self.output_dir.parent / "agent_evidence" / "comparison_views",
            reference_asset=self.source,
        )

    def register_candidate_reassessment(
        self,
        *,
        initiating_tool_call_id: str,
        candidate_satisfies_assessment: bool,
        summary: str,
        evidence: list[str],
        confidence: float,
        source_views_used: list[str],
        candidate_views_used: list[str],
        comparison_views_used: list[str] | None = None,
    ) -> AgentCandidateReassessment:
        """Record the model's visual comparison after an authorized action executes."""
        if not self.agent_orchestrated or self.agent_assessment is None:
            raise AgentWorkflowError("Candidate reassessment requires agent-authored planning")
        if self.candidate_reassessment is not None:
            raise AgentWorkflowError("Candidate visual reassessment is already recorded")
        available_source = {path.name for path in self.render_source_views()}
        available_candidate = {path.name for path in self.render_candidate_views()}
        available_comparison = {path.name for path in self.render_candidate_comparison_views()}
        unknown_source = set(source_views_used) - available_source
        unknown_candidate = set(candidate_views_used) - available_candidate
        comparison_names = comparison_views_used or []
        unknown_comparison = set(comparison_names) - available_comparison
        if unknown_source or unknown_candidate or unknown_comparison:
            raise AgentWorkflowError(
                "Candidate reassessment cites unavailable views: "
                f"source={sorted(unknown_source)}, candidate={sorted(unknown_candidate)}, "
                f"comparison={sorted(unknown_comparison)}"
            )
        payload = {
            "initiating_tool_call_id": initiating_tool_call_id,
            "source_assessment_id": self.agent_assessment.assessment_id,
            "candidate_satisfies_assessment": candidate_satisfies_assessment,
            "summary": summary,
            "evidence": evidence,
            "confidence": confidence,
            "source_views_used": source_views_used,
            "candidate_views_used": candidate_views_used,
            "comparison_views_used": comparison_names,
        }
        digest = sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        reassessment = AgentCandidateReassessment(
            reassessment_id=f"reassessment-{digest}-v1",
            initiating_tool_call_id=initiating_tool_call_id,
            source_assessment_id=self.agent_assessment.assessment_id,
            candidate_satisfies_assessment=candidate_satisfies_assessment,
            summary=summary,
            evidence=tuple(evidence),
            confidence=confidence,
            source_views_used=tuple(source_views_used),
            candidate_views_used=tuple(candidate_views_used),
            comparison_views_used=tuple(comparison_names),
        )
        self.candidate_reassessment = reassessment
        _write_json(self.candidate_reassessment_path, reassessment.model_dump(mode="json"))
        if self.provenance is not None:
            self.provenance = self.provenance.model_copy(
                update={"candidate_reassessment": reassessment}
            )
            _write_json(
                self.output_dir / "provenance.json",
                self.provenance.model_dump(mode="json"),
            )
        self._persist_runtime_state()
        return reassessment

    def register_agent_plan(
        self,
        *,
        initiating_tool_call_id: str,
        disposition: str,
        summary: str,
        evidence: list[str],
        confidence: float,
        semantic_height_axis: Literal["X", "Y", "Z"] | None,
        scale_to_confirmed_height: bool,
        rotation_axis: Literal["X", "Y", "Z"] | None,
        rotation_degrees: Literal[-180, -90, 0, 90, 180],
        ground_to_y_zero: bool,
        rename_invalid_display_names: bool,
        source_views_used: list[str],
        weld_identical_vertices: bool = False,
        clean_degenerate_geometry: bool = False,
        simplify_mesh: bool = False,
        remove_component_ids: list[str] | None = None,
        pivot_target: Literal[
            "PRESERVE", "BOUNDS_CENTER", "FOOTPRINT_CENTER_BOTTOM", "MEASURED_ANCHOR"
        ] = "PRESERVE",
        pivot_anchor_id: str | None = None,
    ) -> RepairPlan:
        """Validate and register one model-authored disposition and exact action preview."""
        if not self.agent_orchestrated:
            raise AgentWorkflowError("Agent-authored planning is disabled for this job")
        if self.inspection is None:
            raise AgentWorkflowError("Inspection must run before agent planning")
        if self.selected_plan is not None or self.agent_assessment is not None:
            raise AgentWorkflowError("This source turn already has a registered assessment")
        # Function-calling models commonly encode an unused optional string as ``""``.
        # Treat that representation as omitted at the deterministic boundary; only a
        # non-empty registered ID carries pivot authority.
        if pivot_anchor_id is not None:
            pivot_anchor_id = pivot_anchor_id.strip() or None
        physical_requested = any(
            (
                scale_to_confirmed_height,
                rotation_degrees != 0,
                ground_to_y_zero,
                pivot_target != "PRESERVE",
            )
        )
        requested_component_ids = remove_component_ids or []
        visual_evidence_requested = (
            physical_requested or bool(requested_component_ids) or simplify_mesh
        )
        # Report-only and return-to-creation conclusions may still rely on rendered
        # evidence. Validate any cited views even when no mutation is requested.
        views_need_validation = visual_evidence_requested or bool(source_views_used)
        available_views: set[str] = (
            {path.name for path in self.render_source_views()} if views_need_validation else set()
        )
        if visual_evidence_requested and not source_views_used:
            raise AgentWorkflowError(
                "Physical, component-selection, and simplification actions require cited visual "
                "evidence"
            )
        unknown_views = set(source_views_used) - available_views
        if unknown_views:
            raise AgentWorkflowError(
                f"Assessment cites unavailable source views: {sorted(unknown_views)}"
            )
        if self.asset_intent is None:
            raise AgentWorkflowError("Agent planning requires a confirmed asset target")
        if (
            ground_to_y_zero
            and rotation_degrees == 0
            and pivot_target == "PRESERVE"
            and self.inspection.geometry is not None
            and abs(self.inspection.geometry.bounds.minimum_m[1]) <= 1e-9
        ):
            raise AgentWorkflowError(
                "Grounding would be a no-op: measured minimum Y is already 0 and the requested "
                "uniform scale preserves it. Submit ground_to_y_zero=false."
            )
        effective_rotation_axis = None if rotation_degrees == 0 else rotation_axis
        if effective_rotation_axis == "Y" and set(source_views_used) != available_views:
            raise AgentWorkflowError(
                "Yaw decisions require all four coordinate-labeled source views"
            )
        if requested_component_ids and set(source_views_used) != available_views:
            raise AgentWorkflowError(
                "Disconnected-component selection requires all four source views"
            )
        pivot_anchor_position_m: tuple[float, float, float] | None = None
        pivot_anchor_label: str | None = None
        if pivot_target == "MEASURED_ANCHOR":
            if pivot_anchor_id is None:
                raise AgentWorkflowError(
                    "A measured pivot target requires an ID from inspect_pivot_anchors_for_job"
                )
            if set(source_views_used) != available_views:
                raise AgentWorkflowError(
                    "Semantic measured-anchor selection requires all four source views"
                )
            inventory = self.inspect_pivot_anchors()
            candidates = {candidate.anchor_id: candidate for candidate in inventory.candidates}
            try:
                anchor = candidates[pivot_anchor_id]
            except KeyError as error:
                raise AgentWorkflowError(
                    "The requested pivot anchor is not registered for this exact source"
                ) from error
            if anchor.kind == "AUTHORED_ORIGIN":
                raise AgentWorkflowError(
                    "Use pivot_target=PRESERVE for the authored origin; it is not a mutation"
                )
            pivot_anchor_position_m = anchor.position_m
            pivot_anchor_label = anchor.label
        elif pivot_anchor_id is not None:
            raise AgentWorkflowError(
                "Only pivot_target=MEASURED_ANCHOR may reference a pivot anchor ID"
            )
        assessment_payload = {
            "initiating_tool_call_id": initiating_tool_call_id,
            "disposition": disposition,
            "summary": summary,
            "evidence": evidence,
            "confidence": confidence,
            "semantic_height_axis": semantic_height_axis,
            "scale_to_confirmed_height": scale_to_confirmed_height,
            "rotation_axis": effective_rotation_axis,
            "rotation_degrees": rotation_degrees,
            "ground_to_y_zero": ground_to_y_zero,
            "pivot_target": pivot_target,
            "pivot_anchor_id": pivot_anchor_id,
            "pivot_anchor_position_m": pivot_anchor_position_m,
            "pivot_anchor_label": pivot_anchor_label,
            "rename_invalid_display_names": rename_invalid_display_names,
            "weld_identical_vertices": weld_identical_vertices,
            "clean_degenerate_geometry": clean_degenerate_geometry,
            "simplify_mesh": simplify_mesh,
            "remove_component_ids": requested_component_ids,
            "source_views_used": source_views_used,
        }
        digest = sha256(
            json.dumps(assessment_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        assessment = AgentRepairAssessment(
            assessment_id=f"assessment-{digest}-v1",
            initiating_tool_call_id=initiating_tool_call_id,
            disposition=AgentDisposition(disposition),
            summary=summary,
            evidence=tuple(evidence),
            confidence=confidence,
            semantic_height_axis=semantic_height_axis,
            scale_to_confirmed_height=scale_to_confirmed_height,
            rotation_axis=effective_rotation_axis,
            rotation_degrees=rotation_degrees,
            ground_to_y_zero=ground_to_y_zero,
            pivot_target=pivot_target,
            pivot_anchor_id=pivot_anchor_id,
            pivot_anchor_position_m=pivot_anchor_position_m,
            pivot_anchor_label=pivot_anchor_label,
            rename_invalid_display_names=rename_invalid_display_names,
            weld_identical_vertices=weld_identical_vertices,
            clean_degenerate_geometry=clean_degenerate_geometry,
            simplify_mesh=simplify_mesh,
            remove_component_ids=tuple(requested_component_ids),
            source_views_used=tuple(source_views_used),
        )
        plan = plan_agent_repairs(
            self.inspection,
            self.profile,
            assessment,
            confirmed_target_height_m=self.asset_intent.target_height_cm / 100.0,
            confirmed_target_dimensions_m=(
                (
                    self.asset_intent.target_dimensions_cm[0] / 100.0,
                    self.asset_intent.target_dimensions_cm[1] / 100.0,
                    self.asset_intent.target_dimensions_cm[2] / 100.0,
                )
                if self.asset_intent.target_dimensions_cm is not None
                else None
            ),
            existing_normalization_root=self._trusted_existing_normalization_root(),
        )
        self.agent_assessment = assessment
        self.full_plan = plan
        self.selected_plan = plan
        self.selection = PlanSelection(
            plan_id=plan.plan_id,
            candidate_ids=tuple(candidate.id for candidate in plan.candidates),
        )
        _write_json(self.agent_assessment_path, assessment.model_dump(mode="json"))
        _write_json(self.output_dir / "repair_plan.json", plan.model_dump(mode="json"))
        self._persist_runtime_state()
        return plan

    def list_candidates(self) -> RepairPlan:
        """Generate the immutable registry of deterministic version-1 candidates."""
        if self.agent_orchestrated:
            raise AgentWorkflowError("The live agent must register its own assessment and actions")
        if self.inspection is None:
            raise AgentWorkflowError("Inspection must run before candidate planning")
        if self.full_plan is None:
            self.full_plan = plan_repairs(self.inspection, self.profile)
        return self.full_plan

    def select_candidates(self, candidate_ids: list[str]) -> PlanSelection:
        """Validate the model's structured selection against the candidate registry."""
        if self.agent_orchestrated:
            raise AgentWorkflowError(
                "Agent-orchestrated plans are selected by their typed proposal"
            )
        plan = self.list_candidates()
        if self.selected_plan is not None or self.selection is not None:
            raise AgentWorkflowError("Repair candidates have already been selected")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise AgentWorkflowError("Repair selection contains duplicate candidate IDs")
        available = {candidate.id for candidate in plan.candidates}
        unknown = set(candidate_ids) - available
        if unknown:
            raise AgentWorkflowError(
                f"Repair selection contains unregistered candidates: {unknown}"
            )
        missing_auto = set(plan.auto_action_ids) - set(candidate_ids)
        if missing_auto:
            raise AgentWorkflowError(
                f"Repair selection omitted AUTO_SAFE candidates: {missing_auto}"
            )
        selected_ids = set(candidate_ids)
        selected_candidates = tuple(
            candidate for candidate in plan.candidates if candidate.id in selected_ids
        )
        selected_auto_ids = tuple(
            candidate_id for candidate_id in plan.auto_action_ids if candidate_id in selected_ids
        )
        selected_approval_ids = tuple(
            candidate_id
            for candidate_id in plan.approval_action_ids
            if candidate_id in selected_ids
        )
        self.selected_plan = RepairPlan(
            plan_id=plan.plan_id,
            inspection_id=plan.inspection_id,
            source_sha256=plan.source_sha256,
            profile_id=plan.profile_id,
            profile_version=plan.profile_version,
            candidates=selected_candidates,
            auto_action_ids=selected_auto_ids,
            approval_action_ids=selected_approval_ids,
            blocked=plan.blocked,
            blocked_reasons=plan.blocked_reasons,
        )
        self.selection = PlanSelection(
            plan_id=plan.plan_id,
            candidate_ids=tuple(candidate.id for candidate in selected_candidates),
        )
        _write_json(
            self.output_dir / "repair_plan.json",
            self.selected_plan.model_dump(mode="json"),
        )
        self._persist_runtime_state()
        return self.selection

    def approval_card(self) -> ApprovalCard | None:
        """Build the single consequential action card, if the selection needs approval."""
        if self.selected_plan is None:
            raise AgentWorkflowError("Candidates must be selected before approval")
        if not self.selected_plan.approval_action_ids:
            return None
        if len(self.selected_plan.approval_action_ids) != 1:
            raise AgentWorkflowError("A plan must contain exactly one approval-required operation")
        candidate_id = self.selected_plan.approval_action_ids[0]
        candidate = next(
            candidate for candidate in self.selected_plan.candidates if candidate.id == candidate_id
        )
        if isinstance(candidate.payload, DegenerateGeometryPayload):
            return ApprovalCard(
                plan_id=self.selected_plan.plan_id,
                candidate_id=candidate.id,
                finding_ids=candidate.finding_ids,
                title="Clean proven degenerate geometry",
                consequence_summary=candidate.payload.consequence_summary,
            )
        if isinstance(candidate.payload, ComponentRemovalPayload):
            removed_ids = tuple(
                component_id
                for primitive in candidate.payload.primitives
                for component_id in primitive.removed_component_ids
            )
            return ApprovalCard(
                plan_id=self.selected_plan.plan_id,
                candidate_id=candidate.id,
                finding_ids=candidate.finding_ids,
                title=(
                    f"Remove {len(removed_ids)} labeled component"
                    f"{'s' if len(removed_ids) != 1 else ''}"
                ),
                consequence_summary=candidate.payload.consequence_summary,
            )
        if isinstance(candidate.payload, MeshSimplificationPayload):
            return ApprovalCard(
                plan_id=self.selected_plan.plan_id,
                candidate_id=candidate.id,
                finding_ids=candidate.finding_ids,
                title=(
                    f"Optimize {candidate.payload.source_triangle_count:,} triangles toward "
                    f"{candidate.payload.target_triangle_count:,}"
                ),
                consequence_summary=candidate.payload.consequence_summary,
            )
        if not isinstance(candidate.payload, NormalizationPayload):
            raise AgentWorkflowError("Approval-required candidate has an unsupported payload")
        labels = {
            "scale": "physical scale",
            "orientation": "upright orientation",
            "grounding": "grounding",
            "pivot": "pivot placement",
        }
        requested = [labels[component.component] for component in candidate.payload.components]
        if len(requested) == 1:
            title = f"Normalize {requested[0]}"
        elif len(requested) == 2:
            title = f"Normalize {requested[0]} and {requested[1]}"
        else:
            title = f"Normalize {', '.join(requested[:-1])}, and {requested[-1]}"
        if (
            self.agent_assessment is not None
            and self.agent_assessment.scale_to_confirmed_height
            and self.agent_assessment.semantic_height_axis is not None
            and self.asset_intent is not None
        ):
            extent_index = {"X": 0, "Y": 1, "Z": 2}[self.agent_assessment.semantic_height_axis]
            before_target_extent_m = candidate.payload.before_bounds.dimensions_m[extent_index]
            expected_target_extent_m = self.asset_intent.target_height_cm / 100.0
            target_extent_label = "Height"
        else:
            before_target_extent_m = max(candidate.payload.before_bounds.dimensions_m)
            expected_target_extent_m = candidate.payload.expected_after_bounds.dimensions_m[1]
            target_extent_label = "Height"
        return ApprovalCard(
            plan_id=self.selected_plan.plan_id,
            candidate_id=candidate.id,
            finding_ids=candidate.finding_ids,
            title=title,
            consequence_summary=candidate.payload.consequence_summary,
            before_bounds=candidate.payload.before_bounds,
            before_target_extent_m=before_target_extent_m,
            proposed_matrix=candidate.payload.proposed_matrix,
            expected_after_bounds=candidate.payload.expected_after_bounds,
            expected_target_extent_m=expected_target_extent_m,
            target_extent_label=target_extent_label,
            components=candidate.payload.components,
        )

    def execute(self, *, approved: bool | None, interrupt_id: str | None) -> RepairOutcome:
        """Apply the selected plan only after a complete approval record exists."""
        if self.selected_plan is None or self.started_at is None:
            raise AgentWorkflowError("A selected plan is required before repair")
        if self.selected_plan.blocked:
            raise AgentWorkflowError("A blocked plan cannot be repaired by the agent")
        if self.outcome is not None:
            return self.outcome
        approval_ids = self.selected_plan.approval_action_ids
        if approval_ids and (approved is None or interrupt_id is None):
            raise AgentWorkflowError("Approval-required repair has no interrupt-bound decision")
        if not approval_ids and (approved is not None or interrupt_id is not None):
            raise AgentWorkflowError(
                "Unexpected approval supplied for a plan with no approval action"
            )
        approvals = {candidate_id: bool(approved) for candidate_id in approval_ids}
        decisions = create_decisions(
            self.selected_plan,
            approvals,
            decided_at=self.clock(),
            source=DecisionSource.USER_INTERACTIVE,
        )
        if interrupt_id is not None:
            records = tuple(
                DecisionRecord.model_validate(
                    {
                        **record.model_dump(mode="python"),
                        "interrupt_id": (
                            interrupt_id if record.candidate_id in approval_ids else None
                        ),
                    }
                )
                for record in decisions.records
            )
            decisions = Decisions(plan_id=decisions.plan_id, records=records)
        self.decisions = decisions
        self._require_output_path(self.candidate_path)
        self.outcome = apply_repairs(
            self.source,
            self.candidate_path,
            self.selected_plan,
            self.decisions,
        )
        self.provenance = build_provenance(
            self.profile,
            self.selected_plan,
            self.decisions,
            self.outcome,
            started_at=self.started_at,
            completed_at=self.clock(),
            profile_policy=self.profile_policy,
            asset_intent=self.asset_intent,
            agent_assessment=self.agent_assessment,
            conversation_turn_index=self.turn_index,
            prior_turns=self.prior_turns,
        )
        _write_json(
            self.output_dir / "decisions.json",
            self.decisions.model_dump(mode="json"),
        )
        _write_json(
            self.output_dir / "provenance.json",
            self.provenance.model_dump(mode="json"),
        )
        self._persist_runtime_state()
        return self.outcome

    def reassess_candidate_after_failure(self) -> RepairPlan:
        """Reinspect a failed candidate and derive, but never execute, a fresh plan."""
        if (
            self.last_verification is None
            or self.last_verification.state is not VerificationState.FAILED
        ):
            raise AgentWorkflowError(
                "Candidate reassessment is allowed only after deterministic verification fails"
            )
        if self.correction_attempts >= 1:
            raise AgentWorkflowError("The single bounded reassessment has already been used")
        if not self.candidate_path.is_file():
            raise AgentWorkflowError("Candidate reassessment requires the failed on-disk GLB")
        self.correction_attempts += 1
        candidate_inspection = inspect_asset(
            self.candidate_path,
            self.profile,
            policy=self.profile_policy,
        )
        correction_plan = plan_repairs(candidate_inspection, self.profile)
        self._persist_runtime_state()
        return correction_plan

    def verify_and_package(self) -> tuple[VerificationResult, JobResult | None]:
        """Independently verify and finalize after at most one candidate reassessment."""
        if self.inspection is None or self.selected_plan is None or self.started_at is None:
            raise AgentWorkflowError("Inspection and a selected plan are required for verification")
        if self.selected_plan.blocked:
            if self.result is not None and self.last_verification is not None:
                return self.last_verification, self.result
            self.decisions = Decisions(plan_id=self.selected_plan.plan_id, records=())
            self.provenance = build_provenance(
                self.profile,
                self.selected_plan,
                self.decisions,
                None,
                started_at=self.started_at,
                completed_at=self.clock(),
                profile_policy=self.profile_policy,
                asset_intent=self.asset_intent,
                agent_assessment=self.agent_assessment,
                conversation_turn_index=self.turn_index,
                prior_turns=self.prior_turns,
            )
            verification = build_blocked_verification(self.selected_plan)
            self.last_verification = verification
            _write_json(
                self.output_dir / "decisions.json",
                self.decisions.model_dump(mode="json"),
            )
            _write_json(
                self.output_dir / "provenance.json",
                self.provenance.model_dump(mode="json"),
            )
            _write_json(
                self.output_dir / "verification.json",
                verification.model_dump(mode="json"),
            )
            (self.output_dir / "report.md").write_text(
                render_final_report(
                    self.inspection,
                    self.selected_plan,
                    self.decisions,
                    verification,
                    None,
                ),
                encoding="utf-8",
                newline="\n",
            )
            zip_path = package_artifacts(self.output_dir, verification)
            artifact_names = tuple(
                sorted(
                    path.name
                    for path in self.output_dir.iterdir()
                    if path.is_file() and path.name != "candidate.glb"
                )
            )
            self.result = JobResult(
                job_id=f"job-{self.inspection.package.file_sha256[:16]}-agent-v1",
                state=JobState.BLOCKED,
                verification_state=verification.state,
                ready_candidate=False,
                artifact_names=artifact_names,
                result_zip=zip_path.name,
                message="Strands workflow blocked repair and returned safe diagnostics.",
            )
            _write_json(
                self.output_dir / "job_result.json",
                self.result.model_dump(mode="json"),
            )
            self._persist_runtime_state()
            return verification, self.result
        if self.decisions is None or self.outcome is None or self.provenance is None:
            raise AgentWorkflowError("Repair must complete before verification")
        visually_consequential_kinds = {
            RepairKind.NORMALIZATION_TRANSFORM,
            RepairKind.WELD_IDENTICAL_VERTICES,
            RepairKind.CLEAN_DEGENERATE_GEOMETRY,
            RepairKind.REMOVE_DISCONNECTED_COMPONENTS,
            RepairKind.SIMPLIFY_MESH,
        }
        visually_consequential_action_ids = {
            candidate.id
            for candidate in self.selected_plan.candidates
            if candidate.kind in visually_consequential_kinds
        }
        requires_visual_reassessment = bool(
            visually_consequential_action_ids.intersection(self.outcome.executed_action_ids)
        )
        if (
            self.agent_orchestrated
            and requires_visual_reassessment
            and self.candidate_reassessment is None
        ):
            raise AgentWorkflowError(
                "Executed physical or topology actions require visual candidate reassessment "
                "before verification"
            )
        if self.result is not None and self.last_verification is not None:
            return self.last_verification, self.result
        if (
            self.last_verification is not None
            and self.last_verification.state is VerificationState.FAILED
            and self.correction_attempts >= 1
        ):
            verification = self.last_verification
        else:
            verification = self.verification_function(
                self.source,
                self.candidate_path,
                self.profile,
                self.inspection,
                self.selected_plan,
                self.decisions,
                self.outcome,
                self.provenance,
            )
            self.last_verification = verification
        if self.candidate_reassessment is not None:
            accepted = self.candidate_reassessment.candidate_satisfies_assessment
            assessment_check = VerificationCheck(
                code="AGENT_VISUAL_REASSESSMENT",
                status=CheckStatus.PASS if accepted else CheckStatus.FAIL,
                description=self.candidate_reassessment.summary,
                basis=CheckBasis.AGENT_ASSESSMENT,
                expected=True,
                actual=accepted,
            )
            verification = verification.model_copy(
                update={
                    "state": verification.state if accepted else VerificationState.FAILED,
                    "checks": (*verification.checks, assessment_check),
                    "remaining_warnings": (
                        verification.remaining_warnings
                        if accepted
                        else (
                            *verification.remaining_warnings,
                            (
                                "The workflow agent did not accept the candidate after visual "
                                "comparison."
                            ),
                        )
                    ),
                }
            )
            self.last_verification = verification
        repaired_inspection = inspect_asset(
            self.candidate_path,
            self.profile,
            policy=self.profile_policy,
        )
        _write_json(
            self.output_dir / "verification.json",
            verification.model_dump(mode="json"),
        )
        (self.output_dir / "report.md").write_text(
            render_final_report(
                self.inspection,
                self.selected_plan,
                self.decisions,
                verification,
                repaired_inspection,
            ),
            encoding="utf-8",
            newline="\n",
        )
        if (
            verification.state is VerificationState.FAILED
            and self.correction_attempts == 0
            and not self.agent_orchestrated
        ):
            self._persist_runtime_state()
            return verification, None

        ready = verification.state in {
            VerificationState.PASSED_PROJECT_READY,
            VerificationState.PASSED_WITH_REMAINING_WARNINGS,
        }
        if ready:
            self.candidate_path.replace(self.output_dir / "repaired.glb")
            state = JobState.COMPLETED
        elif verification.state is VerificationState.BLOCKED:
            state = JobState.BLOCKED
        else:
            state = JobState.FAILED
        zip_path = package_artifacts(self.output_dir, verification)
        contracted_names = (
            "decisions.json",
            "inspection.json",
            "provenance.json",
            "repair_plan.json",
            "report.md",
            "repaired.glb",
            "verification.json",
        )
        packaged_names = tuple(
            sorted(name for name in contracted_names if (self.output_dir / name).is_file())
        )
        self.result = JobResult(
            job_id=f"job-{self.inspection.package.file_sha256[:16]}-agent-v1",
            state=state,
            verification_state=verification.state,
            ready_candidate=ready,
            artifact_names=(*packaged_names, zip_path.name),
            result_zip=zip_path.name,
            message=(
                "Strands workflow completed with a verified candidate."
                if ready
                else "Strands workflow stopped without a project-ready candidate."
            ),
        )
        _write_json(
            self.output_dir / "job_result.json",
            self.result.model_dump(mode="json"),
        )
        self._persist_runtime_state()
        return verification, self.result
