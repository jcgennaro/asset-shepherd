"""Stateful, path-confined stages exposed to the Strands agent."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    ApprovalCard,
    DecisionRecord,
    Decisions,
    DecisionSource,
    InspectionResult,
    JobResult,
    JobState,
    NormalizationPayload,
    PlanSelection,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.planner import plan_repairs
from asset_shepherd.repair import RepairOutcome, apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
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


@dataclass
class AgentJob:
    """One local job whose mutation boundary is its configured output directory."""

    source: Path
    profile_path: Path
    output_dir: Path
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

    def __post_init__(self) -> None:
        """Resolve trusted caller paths before exposing path-free agent tools."""
        self.source = self.source.resolve(strict=True)
        self.profile_path = self.profile_path.resolve(strict=True)
        self.output_dir = self.output_dir.resolve(strict=False)
        if self.source.suffix.lower() != ".glb":
            raise AgentWorkflowError("Agent jobs accept exactly one .glb source")
        if self.output_dir == self.source:
            raise AgentWorkflowError("Agent output directory cannot be the source file")
        self.profile = ProjectProfile.model_validate_json(
            self.profile_path.read_text(encoding="utf-8")
        )

    @property
    def candidate_path(self) -> Path:
        """Return the only mutable GLB candidate path inside this job."""
        return self.output_dir / "candidate.glb"

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
        self.inspection = inspect_asset(self.source, self.profile)
        inspection_path = self.output_dir / "inspection.json"
        self._require_output_path(inspection_path)
        _write_json(inspection_path, self.inspection.model_dump(mode="json"))
        return self.inspection

    def list_candidates(self) -> RepairPlan:
        """Generate the immutable registry of deterministic version-1 candidates."""
        if self.inspection is None:
            raise AgentWorkflowError("Inspection must run before candidate planning")
        if self.full_plan is None:
            self.full_plan = plan_repairs(self.inspection, self.profile)
        return self.full_plan

    def select_candidates(self, candidate_ids: list[str]) -> PlanSelection:
        """Validate the model's structured selection against the candidate registry."""
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
        return self.selection

    def approval_card(self) -> ApprovalCard | None:
        """Build the single combined normalization card, if the selection needs approval."""
        if self.selected_plan is None:
            raise AgentWorkflowError("Candidates must be selected before approval")
        if not self.selected_plan.approval_action_ids:
            return None
        if len(self.selected_plan.approval_action_ids) != 1:
            raise AgentWorkflowError("Version 1 supports exactly one approval-required operation")
        candidate_id = self.selected_plan.approval_action_ids[0]
        candidate = next(
            candidate for candidate in self.selected_plan.candidates if candidate.id == candidate_id
        )
        if not isinstance(candidate.payload, NormalizationPayload):
            raise AgentWorkflowError("Approval-required candidate is not a normalization payload")
        return ApprovalCard(
            plan_id=self.selected_plan.plan_id,
            candidate_id=candidate.id,
            finding_ids=candidate.finding_ids,
            title="Normalize physical scale, upright orientation, and grounding",
            consequence_summary=candidate.payload.consequence_summary,
            before_bounds=candidate.payload.before_bounds,
            proposed_matrix=candidate.payload.proposed_matrix,
            expected_after_bounds=candidate.payload.expected_after_bounds,
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
        )
        _write_json(
            self.output_dir / "decisions.json",
            self.decisions.model_dump(mode="json"),
        )
        _write_json(
            self.output_dir / "provenance.json",
            self.provenance.model_dump(mode="json"),
        )
        return self.outcome

    def retry_once(self) -> RepairOutcome:
        """Reapply the same authorized deterministic plan after one verification failure."""
        if (
            self.last_verification is None
            or self.last_verification.state is not VerificationState.FAILED
        ):
            raise AgentWorkflowError(
                "A correction is allowed only after deterministic verification fails"
            )
        if self.correction_attempts >= 1:
            raise AgentWorkflowError("The single bounded correction attempt has already been used")
        if self.selected_plan is None or self.decisions is None or self.started_at is None:
            raise AgentWorkflowError(
                "Correction requires the existing selected and authorized plan"
            )
        self.correction_attempts += 1
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
        )
        self.last_verification = None
        _write_json(
            self.output_dir / "provenance.json",
            self.provenance.model_dump(mode="json"),
        )
        return self.outcome

    def verify_and_package(self) -> tuple[VerificationResult, JobResult | None]:
        """Independently verify and finalize, allowing at most one pre-final retry."""
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
            return verification, self.result
        if self.decisions is None or self.outcome is None or self.provenance is None:
            raise AgentWorkflowError("Repair must complete before verification")
        if self.result is not None and self.last_verification is not None:
            return self.last_verification, self.result
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
        repaired_inspection = inspect_asset(self.candidate_path, self.profile)
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
        if verification.state is VerificationState.FAILED and self.correction_attempts == 0:
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
        return verification, self.result
