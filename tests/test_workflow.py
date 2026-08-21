"""M6 acceptance tests for verification, packaging, and the full CLI workflow."""

import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest
from jsonschema.validators import validator_for

from asset_shepherd.cli import run_cli
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    Decisions,
    DecisionValue,
    JobState,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.planner import plan_repairs
from asset_shepherd.repair import apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.workflow import build_provenance, run_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
APPROVAL_PATH = PROJECT_ROOT / "examples" / "approve_normalization.json"
FIXED_TIME = datetime(2026, 8, 21, 15, 30, tzinfo=UTC)
PACKAGE_NAMES = {
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
}
SCHEMAS_BY_ARTIFACT = {
    "decisions.json": "decisions.schema.json",
    "inspection.json": "inspection.schema.json",
    "provenance.json": "provenance.schema.json",
    "repair_plan.json": "repair_plan.schema.json",
    "verification.json": "verification.schema.json",
}


def _profile() -> ProjectProfile:
    return ProjectProfile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def _fixed_clock() -> datetime:
    return FIXED_TIME


def _assert_json_artifacts_match_schemas(output: Path) -> None:
    for artifact_name, schema_name in SCHEMAS_BY_ARTIFACT.items():
        instance = json.loads((output / artifact_name).read_text(encoding="utf-8"))
        schema = json.loads((PROJECT_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        validator_class = validator_for(schema)
        validator_class.check_schema(schema)
        validator_class(schema).validate(instance)


def test_full_approved_workflow_verifies_and_packages_every_artifact(tmp_path: Path) -> None:
    """One call completes inspect, plan, approve, repair, verify, and package."""
    source_before = BROKEN_PATH.read_bytes()
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first = run_workflow(
        BROKEN_PATH,
        _profile(),
        {"normalize-root-v1": True},
        first_output,
        clock=_fixed_clock,
    )
    run_workflow(
        BROKEN_PATH,
        _profile(),
        {"normalize-root-v1": True},
        second_output,
        clock=_fixed_clock,
    )
    assert first.state is JobState.COMPLETED
    assert first.ready_candidate
    assert first.verification_state is VerificationState.PASSED_WITH_REMAINING_WARNINGS
    assert BROKEN_PATH.read_bytes() == source_before
    assert (first_output / "repaired.glb").read_bytes() == (
        second_output / "repaired.glb"
    ).read_bytes()
    assert (first_output / "result.zip").read_bytes() == (second_output / "result.zip").read_bytes()

    verification = VerificationResult.model_validate_json(
        (first_output / "verification.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (first_output / "provenance.json").read_text(encoding="utf-8")
    )
    plan = RepairPlan.model_validate_json(
        (first_output / "repair_plan.json").read_text(encoding="utf-8")
    )
    decisions = Decisions.model_validate_json(
        (first_output / "decisions.json").read_text(encoding="utf-8")
    )
    assert all(check.status.value == "PASS" for check in verification.checks)
    assert verification.second_plan_candidate_count == 0
    assert verification.output_sha256 == provenance.output_sha256
    assert len(provenance.executed_actions) == len(plan.candidates) == 10
    assert any(
        record.candidate_id == "normalize-root-v1" and record.decision is DecisionValue.APPROVED
        for record in decisions.records
    )
    assert provenance.started_at == provenance.completed_at == FIXED_TIME
    assert provenance.commit_sha != "unknown"
    assert set(provenance.library_versions) == {
        "Pillow",
        "numpy",
        "pydantic",
        "pygltflib",
        "trimesh",
    }
    with ZipFile(first_output / "result.zip") as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES
        assert archive.read("repaired.glb") == (first_output / "repaired.glb").read_bytes()
    _assert_json_artifacts_match_schemas(first_output)
    report = (first_output / "report.md").read_text(encoding="utf-8")
    assert "## Before and after" in report
    assert "## Verification checks" in report
    assert "MATERIAL_BUDGET_EXCEEDED" in report


def test_rejected_normalization_is_preserved_through_verification(tmp_path: Path) -> None:
    """The full reject path packages safe renames without applying normalization."""
    output = tmp_path / "rejected"
    result = run_workflow(
        BROKEN_PATH,
        _profile(),
        {"normalize-root-v1": False},
        output,
        clock=_fixed_clock,
    )
    assert result.state is JobState.COMPLETED
    verification = VerificationResult.model_validate_json(
        (output / "verification.json").read_text(encoding="utf-8")
    )
    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (output / "provenance.json").read_text(encoding="utf-8")
    )
    assert verification.state is VerificationState.PASSED_WITH_REMAINING_WARNINGS
    assert verification.second_plan_candidate_count == 0
    normalization_record = next(
        record for record in decisions.records if record.candidate_id == "normalize-root-v1"
    )
    assert normalization_record.decision is DecisionValue.REJECTED
    assert "normalize-root-v1" not in {
        action.candidate_id for action in provenance.executed_actions
    }
    assert {
        "HEIGHT_OUT_OF_RANGE",
        "ORIENTATION_NOT_Y_UP",
        "NOT_GROUNDED",
    } <= {warning.partition(":")[0] for warning in verification.remaining_warnings}
    rejected_check = next(
        check for check in verification.checks if check.code == "REJECTED_NORMALIZATION_NOT_APPLIED"
    )
    assert rejected_check.status.value == "PASS"
    repaired = inspect_asset(output / "repaired.glb", _profile())
    assert repaired.geometry is not None
    assert repaired.geometry.dominant_dimension_axis == "X"
    assert repaired.geometry.ground_relationship == "FLOATS_ABOVE"


def test_clean_control_proposes_nothing_and_preserves_glb_bytes(tmp_path: Path) -> None:
    """A compliant asset is packaged without repairs or unnecessary serialization."""
    output = tmp_path / "clean-control"
    source_bytes = CLEAN_PATH.read_bytes()
    result = run_workflow(CLEAN_PATH, _profile(), {}, output, clock=_fixed_clock)
    plan = RepairPlan.model_validate_json((output / "repair_plan.json").read_text(encoding="utf-8"))
    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (output / "provenance.json").read_text(encoding="utf-8")
    )
    verification = VerificationResult.model_validate_json(
        (output / "verification.json").read_text(encoding="utf-8")
    )

    assert result.state is JobState.COMPLETED
    assert result.verification_state is VerificationState.PASSED_PROJECT_READY
    assert plan.candidates == ()
    assert decisions.records == ()
    assert provenance.executed_actions == ()
    assert (output / "repaired.glb").read_bytes() == source_bytes
    assert verification.source_sha256 == verification.output_sha256
    assert all(check.status.value == "PASS" for check in verification.checks)
    with ZipFile(output / "result.zip") as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES
        assert archive.read("repaired.glb") == source_bytes
    _assert_json_artifacts_match_schemas(output)


def test_invalid_input_returns_diagnostic_package_without_ready_asset(tmp_path: Path) -> None:
    """A blocked job packages diagnostics and never labels a repaired GLB ready."""
    invalid = tmp_path / "invalid.glb"
    invalid.write_bytes(b"invalid")
    output = tmp_path / "blocked"
    result = run_workflow(invalid, _profile(), {}, output, clock=_fixed_clock)
    assert result.state is JobState.BLOCKED
    assert not result.ready_candidate
    assert result.verification_state is VerificationState.BLOCKED
    assert not (output / "repaired.glb").exists()
    with ZipFile(output / "result.zip") as archive:
        assert "repaired.glb" not in archive.namelist()
        assert set(archive.namelist()) == PACKAGE_NAMES - {"repaired.glb"}


def test_tampered_candidate_fails_verification(tmp_path: Path) -> None:
    """Fresh-disk parse and hash failures prevent project-ready status."""
    profile = _profile()
    original = inspect_asset(BROKEN_PATH, profile)
    plan = plan_repairs(original, profile)
    decisions = create_decisions(
        plan,
        {"normalize-root-v1": True},
        decided_at=FIXED_TIME,
    )
    candidate = tmp_path / "candidate.glb"
    outcome = apply_repairs(BROKEN_PATH, candidate, plan, decisions)
    provenance = build_provenance(
        profile,
        plan,
        decisions,
        outcome,
        started_at=FIXED_TIME,
        completed_at=FIXED_TIME,
    )
    candidate.write_bytes(candidate.read_bytes()[:8])
    verification = verify_repair(
        BROKEN_PATH,
        candidate,
        profile,
        original,
        plan,
        decisions,
        outcome,
        provenance,
    )
    assert verification.state is VerificationState.FAILED
    assert any(check.status.value == "FAIL" for check in verification.checks)


def test_run_cli_executes_documented_demo_command_shape(tmp_path: Path) -> None:
    """The documented one-command workflow produces a verified result ZIP."""
    output = tmp_path / "cli-output"
    exit_code = run_cli(
        [
            "run",
            str(BROKEN_PATH),
            "--profile",
            str(PROFILE_PATH),
            "--approvals",
            str(APPROVAL_PATH),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert (output / "result.zip").is_file()
    assert (output / "job_result.json").is_file()
    with pytest.raises(FileExistsError):
        run_workflow(
            BROKEN_PATH,
            _profile(),
            {"normalize-root-v1": True},
            output,
            clock=_fixed_clock,
        )
