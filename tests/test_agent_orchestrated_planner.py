"""D036 tests for model-authored target-dependent action previews."""

from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentDisposition,
    AgentRepairAssessment,
    AssetIntentProvenance,
    AssetTargetUse,
    Bounds3D,
    NormalizationPayload,
    ProjectProfile,
    Provenance,
)
from asset_shepherd.planner import plan_agent_repairs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"


def _profile() -> ProjectProfile:
    return ProjectProfile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def _intent(height_cm: float = 180.0) -> AssetIntentProvenance:
    return AssetIntentProvenance(
        intent_id="1" * 32,
        original_description="A standing robot character for a game, approximately human sized.",
        target_use=AssetTargetUse.RIG_READY_CHARACTER,
        target_height_cm=height_cm,
        confirmed_story=(
            "A standing robot character approximately 1.8 meters tall for later rigging."
        ),
        confirmed_at=datetime(2026, 8, 23, tzinfo=UTC),
        canonical_sha256="2" * 64,
    )


def _write_fake_views(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("front.png", "right.png", "back.png", "left.png"):
        (root / name).write_bytes(b"recorded-test-view")


def _long_quadruped_bounds() -> Bounds3D:
    return Bounds3D(
        minimum_m=(-0.2353515625, 0.0, -0.4990234375),
        maximum_m=(0.2353515625, 0.462890625, 0.4990234375),
        dimensions_m=(0.470703125, 0.462890625, 0.998046875),
        minimum_cm=(-23.53515625, 0.0, -49.90234375),
        maximum_cm=(23.53515625, 46.2890625, 49.90234375),
        dimensions_cm=(47.0703125, 46.2890625, 99.8046875),
    )


def test_longest_axis_does_not_manufacture_quadruped_rotation() -> None:
    """A grounded long-bodied quadruped scales on semantic Y without a hidden Z-to-Y turn."""
    profile = _profile()
    inspection = inspect_asset(CLEAN_PATH, profile)
    assert inspection.geometry is not None
    geometry = inspection.geometry.model_copy(
        update={
            "bounds": _long_quadruped_bounds(),
            "dominant_dimension_axis": "Z",
            "ground_relationship": "GROUNDED",
        }
    )
    inspection = inspection.model_copy(update={"geometry": geometry})
    assessment = AgentRepairAssessment(
        assessment_id="assessment-0123456789abcdef-v1",
        disposition=AgentDisposition.REPAIR,
        summary="The puppy is upright and grounded, but its source Y height is below the target.",
        evidence=(
            "All four rendered views show the feet below the body.",
            "The source is grounded at minimum Y = 0 m.",
            "Source Y height is 0.462890625 m; source Z is body length.",
        ),
        confidence=0.96,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=False,
        source_views_used=("front.png", "right.png", "back.png", "left.png"),
    )

    plan = plan_agent_repairs(
        inspection,
        profile,
        assessment,
        confirmed_target_height_m=4.5,
    )

    assert plan.planning_authority == "AGENT_ORCHESTRATED"
    assert plan.agent_assessment_id == assessment.assessment_id
    normalization = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )
    assert [component.component for component in normalization.components] == ["scale"]
    assert normalization.expected_after_bounds.dimensions_m[1] == pytest.approx(4.5)
    assert normalization.expected_after_bounds.dimensions_m[2] > 9.0
    matrix = normalization.proposed_matrix
    assert matrix[0][1:] == (0.0, 0.0, 0.0)
    assert matrix[1][0] == 0.0
    assert matrix[1][2:] == (0.0, 0.0)
    assert matrix[2][0:2] == (0.0, 0.0)


def test_agent_plan_contains_only_explicitly_requested_transform_components() -> None:
    """The preview layer does not silently add grounding or orientation to a scale request."""
    profile = _profile()
    inspection = inspect_asset(CLEAN_PATH, profile)
    assessment = AgentRepairAssessment(
        assessment_id="assessment-fedcba9876543210-v1",
        disposition=AgentDisposition.REPAIR,
        summary="The rendered character is already upright and grounded but needs a scale change.",
        evidence=("Source Y is the visible character height.",),
        confidence=0.9,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
        source_views_used=("front.png",),
    )

    plan = plan_agent_repairs(
        inspection,
        profile,
        assessment,
        confirmed_target_height_m=1.8,
    )
    payload = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )
    assert tuple(component.component for component in payload.components) == ("scale",)


def test_nonrepair_disposition_cannot_smuggle_mutation() -> None:
    """Typed assessment validation rejects an action attached to an accept disposition."""
    with pytest.raises(ValueError, match="Only a REPAIR disposition"):
        AgentRepairAssessment(
            assessment_id="assessment-aaaaaaaaaaaaaaaa-v1",
            disposition=AgentDisposition.ACCEPT,
            summary="The asset matches the confirmed target and needs no supported correction.",
            evidence=("Rendered pose and measured size agree.",),
            confidence=0.9,
            semantic_height_axis="Y",
            scale_to_confirmed_height=True,
        )


def test_executed_agent_action_requires_and_packages_visual_reassessment(
    tmp_path: Path,
) -> None:
    """A live-authority candidate cannot verify before the model compares before and after."""
    output = tmp_path / "output"
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()
    evidence_root = output.parent / "agent_evidence"
    _write_fake_views(evidence_root / "source_views")
    plan = job.register_agent_plan(
        initiating_tool_call_id="unit-plan-tool-call",
        disposition="REPAIR",
        summary="The robot is upright and grounded; only its physical height needs normalization.",
        evidence=["Source Y is semantic height in all four standardized views."],
        confidence=0.95,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    assert plan.planning_authority == "AGENT_ORCHESTRATED"
    job.execute(approved=True, interrupt_id="test-interrupt-v1")

    with pytest.raises(AgentWorkflowError, match="visual candidate reassessment"):
        job.verify_and_package()

    _write_fake_views(evidence_root / "candidate_views")
    reassessment = job.register_candidate_reassessment(
        initiating_tool_call_id="unit-reassessment-tool-call",
        candidate_satisfies_assessment=True,
        summary="The candidate keeps the source pose and reaches the requested physical scale.",
        evidence=[
            "All four candidate views preserve the source pose and silhouette.",
            "The deterministic preview supplies the exact target bounds.",
        ],
        confidence=0.94,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
        candidate_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    verification, result = job.verify_and_package()

    assert result is not None
    assert any(check.code == "AGENT_VISUAL_REASSESSMENT" for check in verification.checks)
    provenance = Provenance.model_validate_json(
        (output / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance.agent_assessment is not None
    assert provenance.agent_assessment.assessment_id == plan.agent_assessment_id
    assert provenance.agent_assessment.initiating_tool_call_id == "unit-plan-tool-call"
    assert provenance.candidate_reassessment == reassessment
    assert reassessment.initiating_tool_call_id == "unit-reassessment-tool-call"
    with ZipFile(output / "result.zip") as archive:
        packaged = Provenance.model_validate_json(archive.read("provenance.json"))
    assert packaged.candidate_reassessment == reassessment
