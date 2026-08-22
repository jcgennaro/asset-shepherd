"""Complete deterministic inspect-to-package workflow."""

import json
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AssetIntentProvenance,
    CheckStatus,
    Decisions,
    DecisionSource,
    ExecutedAction,
    InspectionResult,
    JobResult,
    JobState,
    ProfilePolicyProvenance,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationCheck,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.planner import plan_repairs
from asset_shepherd.profile_policy import build_profile_policy_provenance
from asset_shepherd.repair import RepairOutcome, apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair

_PACKAGE_NAMES = (
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")


def _application_commit() -> str:
    configured = os.environ.get("ASSET_SHEPHERD_COMMIT_SHA")
    if configured:
        return configured
    repository = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else "unknown"


def _library_versions() -> dict[str, str]:
    distributions = ("numpy", "Pillow", "pydantic", "pygltflib", "trimesh")
    versions: dict[str, str] = {}
    for distribution in distributions:
        try:
            versions[distribution] = version(distribution)
        except PackageNotFoundError:
            versions[distribution] = "unknown"
    return versions


def build_provenance(
    profile: ProjectProfile,
    plan: RepairPlan,
    decisions: Decisions,
    outcome: RepairOutcome | None,
    *,
    started_at: datetime,
    completed_at: datetime,
    profile_policy: ProfilePolicyProvenance | None = None,
    asset_intent: AssetIntentProvenance | None = None,
) -> Provenance:
    """Build provenance from the exact plan, decisions, and repair outcome."""
    candidates = {candidate.id: candidate for candidate in plan.candidates}
    records = {record.candidate_id: record for record in decisions.records}
    executed_actions = ()
    output_sha256: str | None = None
    if outcome is not None:
        output_sha256 = outcome.output_sha256
        executed_actions = tuple(
            ExecutedAction(
                candidate_id=candidate_id,
                kind=candidates[candidate_id].kind,
                finding_ids=candidates[candidate_id].finding_ids,
                authorization=records[candidate_id].decision,
            )
            for candidate_id in outcome.executed_action_ids
        )
    try:
        application_version = version("asset-shepherd")
    except PackageNotFoundError:
        application_version = "0+unknown"
    return Provenance(
        source_sha256=plan.source_sha256,
        output_sha256=output_sha256,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        profile_policy=profile_policy or build_profile_policy_provenance(profile),
        asset_intent=asset_intent,
        application_version=application_version,
        commit_sha=_application_commit(),
        library_versions=_library_versions(),
        executed_actions=executed_actions,
        decisions=decisions.records,
        started_at=started_at,
        completed_at=completed_at,
    )


def build_blocked_verification(plan: RepairPlan) -> VerificationResult:
    """Build deterministic diagnostics for a plan that cannot be repaired safely."""
    reason = "; ".join(plan.blocked_reasons) or "Repair plan is blocked"
    return VerificationResult(
        verification_id=f"verification-{plan.source_sha256[:16]}-blocked",
        source_sha256=plan.source_sha256,
        output_sha256=None,
        state=VerificationState.BLOCKED,
        checks=(
            VerificationCheck(
                code="REPAIR_ELIGIBILITY",
                status=CheckStatus.BLOCKED,
                description=reason,
                expected="ELIGIBLE_STATIC_MESH",
                actual=reason,
            ),
        ),
        remaining_warnings=(reason,),
        second_plan_candidate_count=0,
    )


def render_final_report(
    original: InspectionResult,
    plan: RepairPlan,
    decisions: Decisions,
    verification: VerificationResult,
    repaired: InspectionResult | None,
) -> str:
    """Render the contracted before/after and verification report."""
    lines = [
        "# Asset Shepherd Repair Report",
        "",
        f"- Source: `{original.source_filename}`",
        f"- Source SHA-256: `{original.package.file_sha256}`",
        f"- Repair eligibility: `{original.repair_eligibility}`",
        f"- Verification: `{verification.state}`",
        "",
        "## Before and after",
        "",
    ]
    if original.geometry is not None:
        before = original.geometry.bounds.dimensions_m
        lines.append(f"- Before dimensions: {before[0]:.6g} x {before[1]:.6g} x {before[2]:.6g} m")
    if repaired is not None and repaired.geometry is not None:
        after = repaired.geometry.bounds.dimensions_m
        lines.append(f"- After dimensions: {after[0]:.6g} x {after[1]:.6g} x {after[2]:.6g} m")
        lines.append(f"- After minimum Y: {repaired.geometry.bounds.minimum_m[1]:.9g} m")
    lines.extend(("", "## Findings", ""))
    if original.findings:
        lines.extend(
            f"- `{finding.code}` ({finding.severity}, {finding.action_class}): {finding.title}"
            for finding in original.findings
        )
    else:
        lines.append("- No project-policy findings.")
    lines.extend(("", "## Decisions and actions", ""))
    candidate_by_id = {candidate.id: candidate for candidate in plan.candidates}
    if decisions.records:
        lines.extend(
            f"- `{record.candidate_id}`: {record.decision} via {record.source}; "
            f"{candidate_by_id[record.candidate_id].description}"
            for record in decisions.records
        )
    else:
        lines.append("- No repair actions were eligible.")
    lines.extend(("", "## Verification checks", ""))
    lines.extend(
        f"- `{check.code}`: {check.status} — {check.description} (basis: {check.basis})"
        for check in verification.checks
    )
    lines.extend(("", "## Remaining warnings", ""))
    if verification.remaining_warnings:
        lines.extend(f"- {warning}" for warning in verification.remaining_warnings)
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def package_artifacts(output_dir: Path, verification: VerificationResult) -> Path:
    """Create a deterministic ZIP containing only safe contracted artifacts."""
    names = tuple(
        name
        for name in _PACKAGE_NAMES
        if name != "repaired.glb"
        or verification.state
        in {
            VerificationState.PASSED_PROJECT_READY,
            VerificationState.PASSED_WITH_REMAINING_WARNINGS,
        }
    )
    missing = [name for name in names if not (output_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Cannot package missing artifacts: {missing}")
    zip_path = output_dir / "result.zip"
    with ZipFile(zip_path, mode="w") as archive:
        for name in sorted(names):
            info = ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output_dir / name).read_bytes())
    return zip_path


def run_workflow(
    source: Path,
    profile: ProjectProfile,
    approvals: dict[str, bool],
    output_dir: Path,
    *,
    clock: Callable[[], datetime] = _utc_now,
    decision_source: DecisionSource = DecisionSource.USER_APPROVAL_FILE,
) -> JobResult:
    """Run inspect, plan, approve, repair, verify, and package without a network."""
    output_dir.mkdir(parents=True, exist_ok=False)
    started_at = clock()
    original = inspect_asset(source, profile)
    plan = plan_repairs(original, profile)
    _write_json(output_dir / "inspection.json", original.model_dump(mode="json"))
    _write_json(output_dir / "repair_plan.json", plan.model_dump(mode="json"))

    if plan.blocked:
        decisions = Decisions(plan_id=plan.plan_id, records=())
        provenance = build_provenance(
            profile,
            plan,
            decisions,
            None,
            started_at=started_at,
            completed_at=clock(),
        )
        verification = build_blocked_verification(plan)
        repaired_inspection = None
        job_state = JobState.BLOCKED
    else:
        decisions = create_decisions(
            plan,
            approvals,
            decided_at=clock(),
            source=decision_source,
        )
        candidate_path = output_dir / "candidate.glb"
        outcome = apply_repairs(source, candidate_path, plan, decisions)
        provenance = build_provenance(
            profile,
            plan,
            decisions,
            outcome,
            started_at=started_at,
            completed_at=clock(),
        )
        verification = verify_repair(
            source,
            candidate_path,
            profile,
            original,
            plan,
            decisions,
            outcome,
            provenance,
        )
        repaired_inspection = inspect_asset(candidate_path, profile)
        if verification.state in {
            VerificationState.PASSED_PROJECT_READY,
            VerificationState.PASSED_WITH_REMAINING_WARNINGS,
        }:
            candidate_path.replace(output_dir / "repaired.glb")
            job_state = JobState.COMPLETED
        else:
            job_state = JobState.FAILED

    _write_json(output_dir / "decisions.json", decisions.model_dump(mode="json"))
    _write_json(output_dir / "verification.json", verification.model_dump(mode="json"))
    _write_json(output_dir / "provenance.json", provenance.model_dump(mode="json"))
    (output_dir / "report.md").write_text(
        render_final_report(original, plan, decisions, verification, repaired_inspection),
        encoding="utf-8",
        newline="\n",
    )
    zip_path = package_artifacts(output_dir, verification)
    packaged_names = tuple(sorted(name for name in _PACKAGE_NAMES if (output_dir / name).is_file()))
    ready = verification.state in {
        VerificationState.PASSED_PROJECT_READY,
        VerificationState.PASSED_WITH_REMAINING_WARNINGS,
    }
    return JobResult(
        job_id=f"job-{original.package.file_sha256[:16]}-v1",
        state=job_state,
        verification_state=verification.state,
        ready_candidate=ready,
        artifact_names=(*packaged_names, zip_path.name),
        result_zip=zip_path.name,
        message=(
            "Deterministic workflow completed with a verified candidate."
            if ready
            else "Deterministic workflow stopped without a project-ready candidate."
        ),
    )
