"""D036 tests for model-authored target-dependent action previews."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image, ImageDraw

from asset_shepherd.agent_job import (
    GLTF_SOURCE_VIEW_CONTRACT,
    AgentJob,
    AgentWorkflowError,
)
from asset_shepherd.glb import add_normalization_root, load_glb, save_glb, world_bounds
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentDisposition,
    AgentRepairAssessment,
    AssetIntentProvenance,
    AssetTargetUse,
    Bounds3D,
    NormalizationPayload,
    ProjectProfile,
    ProposalDisposition,
    ProposalLane,
    ProposalResponse,
    Provenance,
)
from asset_shepherd.planner import plan_agent_repairs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"


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
        image = Image.new("RGB", (160, 160), (8, 14, 18))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((35, 28, 125, 132), radius=12, fill=(96, 154, 178))
        image.save(root / name, format="PNG")
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((35, 28, 125, 132), radius=12, fill=255)
        mask.save(root / name.replace(".png", ".mask.png"), format="PNG")
    (root / "view_contract.json").write_text(
        json.dumps(GLTF_SOURCE_VIEW_CONTRACT),
        encoding="utf-8",
    )


def _record_successful_candidate_reassessment(job: AgentJob, suffix: str) -> None:
    evidence_root = job.output_dir.parent / "agent_evidence"
    _write_fake_views(evidence_root / "candidate_views")
    _write_fake_views(evidence_root / "comparison_views")
    job.register_candidate_reassessment(
        initiating_tool_call_id=f"reassessment-{suffix}",
        candidate_satisfies_assessment=True,
        summary="The isolated and shared-scale views show the requested bounded change.",
        evidence=["The candidate remains visible and its silhouette is preserved in every view."],
        confidence=0.95,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
        candidate_views_used=["front.png", "right.png", "back.png", "left.png"],
        comparison_views_used=["front.png", "right.png", "back.png", "left.png"],
    )


def _complete_accept_turn(job: AgentJob, suffix: str) -> None:
    job.inspect()
    job.register_agent_plan(
        initiating_tool_call_id=f"accept-tool-{suffix}",
        disposition="ACCEPT",
        summary="The current candidate needs no additional supported mutation in this turn.",
        evidence=["Objective inspection reports a valid eligible static GLB."],
        confidence=0.9,
        semantic_height_axis=None,
        scale_to_confirmed_height=False,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=False,
        source_views_used=[],
    )
    job.execute(approved=None, interrupt_id=None)
    _, result = job.verify_and_package()
    assert result is not None


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


def test_plan_feedback_archives_without_executing_and_reopens_agent_planning(
    tmp_path: Path,
) -> None:
    """A commented proposal returns to the agent without creating a candidate GLB."""
    output = tmp_path / "output"
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(height_cm=360.0),
        agent_orchestrated=True,
    )
    job.inspect()
    _write_fake_views(output.parent / "agent_evidence" / "source_views")
    plan = job.register_agent_plan(
        initiating_tool_call_id="initial-plan-tool-call",
        disposition="REPAIR",
        summary="Uniformly scale the upright model to the proposed target.",
        evidence=["The source views show Y as the semantic height axis."],
        confidence=0.94,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    job.set_pending_interrupt("pending-plan-feedback-v1")
    responses = (
        ProposalResponse(
            lane=ProposalLane.SIZE_AND_POSE,
            disposition=ProposalDisposition.COMMENT,
            comment="Keep the present scale; only inspect the asset.",
        ),
    )

    recorded = job.request_plan_revision(responses)
    assert recorded == responses
    assert job.outcome is None
    assert job.selected_plan is None
    assert job.agent_assessment is None
    assert job.pending_interrupt_id is None
    assert not (output / "candidate.glb").exists()
    assert not (output / "repair_plan.json").exists()
    revision_root = output.parent / "plan_revisions" / "turn-000-revision-001"
    archived_plan = json.loads((revision_root / "repair_plan.json").read_text())
    revision_request = json.loads((revision_root / "revision_request.json").read_text())
    assert archived_plan["plan_id"] == plan.plan_id
    assert revision_request["responses"][0]["lane"] == "SIZE_AND_POSE"
    assert revision_request["responses"][0]["disposition"] == "COMMENT"


def test_approximate_target_box_uses_one_robust_uniform_scale() -> None:
    """Unequal per-axis target factors never become non-uniform mesh scaling."""
    profile = _profile()
    inspection = inspect_asset(CLEAN_PATH, profile)
    assert inspection.geometry is not None
    source_dimensions = inspection.geometry.bounds.dimensions_m
    target_dimensions = (
        source_dimensions[0] * 6.0,
        source_dimensions[1] * 3.0,
        source_dimensions[2] * 6.2,
    )
    assessment = AgentRepairAssessment(
        assessment_id="assessment-1234567890abcdef-v1",
        disposition=AgentDisposition.REPAIR,
        summary="The approximate target box requires one proportional scale adjustment.",
        evidence=("The target dimensions are approximate and the source proportions must remain.",),
        confidence=0.9,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
    )

    plan = plan_agent_repairs(
        inspection,
        profile,
        assessment,
        confirmed_target_height_m=target_dimensions[1],
        confirmed_target_dimensions_m=target_dimensions,
    )
    payload = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )

    diagonal = tuple(payload.proposed_matrix[index][index] for index in range(3))
    expected_factor = (6.0 * 3.0 * 6.2) ** (1.0 / 3.0)
    assert diagonal == pytest.approx((expected_factor,) * 3)
    assert payload.expected_after_bounds.dimensions_m == pytest.approx(
        tuple(value * expected_factor for value in source_dimensions)
    )
    assert "log-space best fit" in payload.components[0].evidence
    assert "Residual differences are expected" in payload.components[0].evidence


def test_agent_can_recenter_pivot_to_footprint_without_inventing_scale_or_rotation() -> None:
    """A requested pivot target becomes one exact translation in the grouped root action."""
    profile = _profile()
    inspection = inspect_asset(CLEAN_PATH, profile)
    assert inspection.geometry is not None
    bounds = Bounds3D(
        minimum_m=(1.0, 2.0, 3.0),
        maximum_m=(5.0, 6.0, 9.0),
        dimensions_m=(4.0, 4.0, 6.0),
        minimum_cm=(100.0, 200.0, 300.0),
        maximum_cm=(500.0, 600.0, 900.0),
        dimensions_cm=(400.0, 400.0, 600.0),
    )
    geometry = inspection.geometry.model_copy(update={"bounds": bounds})
    inspection = inspection.model_copy(update={"geometry": geometry})
    assessment = AgentRepairAssessment(
        assessment_id="assessment-2468ace02468ace0-v1",
        disposition=AgentDisposition.REPAIR,
        summary="This grounded static prop needs its pivot at the center of its footprint.",
        evidence=("World bounds place the footprint center-bottom at (3, 2, 6) m.",),
        confidence=0.95,
        pivot_target="FOOTPRINT_CENTER_BOTTOM",
        source_views_used=("front.png", "right.png"),
    )

    plan = plan_agent_repairs(
        inspection,
        profile,
        assessment,
        confirmed_target_height_m=4.0,
    )
    payload = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )

    assert payload.pivot_target == "FOOTPRINT_CENTER_BOTTOM"
    assert tuple(component.component for component in payload.components) == ("pivot",)
    assert payload.proposed_matrix[0][3] == pytest.approx(-3.0)
    assert payload.proposed_matrix[1][3] == pytest.approx(-2.0)
    assert payload.proposed_matrix[2][3] == pytest.approx(-6.0)
    assert payload.expected_after_bounds.minimum_m == pytest.approx((-2.0, 0.0, -3.0))
    assert payload.expected_after_bounds.maximum_m == pytest.approx((2.0, 4.0, 3.0))


def test_agent_can_select_only_a_registered_geometry_pivot_anchor(tmp_path: Path) -> None:
    """Semantic pivot placement resolves an opaque measured ID, never model-supplied XYZ."""
    output = tmp_path / "output"
    _write_fake_views(output.parent / "agent_evidence" / "source_views")
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()
    inventory = job.inspect_pivot_anchors()
    anchor = next(
        candidate for candidate in inventory.candidates if candidate.kind == "LONG_AXIS_END_REGION"
    )

    plan = job.register_agent_plan(
        initiating_tool_call_id="measured-pivot-tool-call",
        disposition="REPAIR",
        summary="Use the visually identified end-region landmark as the placement origin.",
        evidence=["All four coordinate views place the requested feature in this end region."],
        confidence=0.92,
        semantic_height_axis=None,
        scale_to_confirmed_height=False,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        pivot_target="MEASURED_ANCHOR",
        pivot_anchor_id=anchor.anchor_id,
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    payload = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )

    assert payload.pivot_target == "MEASURED_ANCHOR"
    assert payload.pivot_anchor_id == anchor.anchor_id
    assert payload.pivot_anchor_position_m == anchor.position_m
    transformed_anchor = np.asarray(payload.proposed_matrix) @ np.asarray([*anchor.position_m, 1.0])
    assert transformed_anchor[:3] == pytest.approx((0.0, 0.0, 0.0), abs=1e-10)
    assert (output / "pivot_anchors.json").is_file()
    job.execute(approved=True, interrupt_id="measured-pivot-approval-v1")
    _record_successful_candidate_reassessment(job, "measured-pivot")
    verification, result = job.verify_and_package()
    assert result is not None
    pivot_check = next(
        check for check in verification.checks if check.code == "APPROVED_PIVOT_AT_TARGET"
    )
    assert pivot_check.status.value == "PASS"


def test_agent_cannot_invent_a_measured_pivot_anchor_id(tmp_path: Path) -> None:
    """An unregistered semantic point fails before an assessment or plan is persisted."""
    output = tmp_path / "output"
    _write_fake_views(output.parent / "agent_evidence" / "source_views")
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()

    with pytest.raises(AgentWorkflowError, match="not registered for this exact source"):
        job.register_agent_plan(
            initiating_tool_call_id="invented-pivot-tool-call",
            disposition="REPAIR",
            summary="Move an invented semantic point to the asset origin.",
            evidence=["The requested point is not in the measured inventory."],
            confidence=0.4,
            semantic_height_axis=None,
            scale_to_confirmed_height=False,
            rotation_axis=None,
            rotation_degrees=0,
            ground_to_y_zero=False,
            pivot_target="MEASURED_ANCHOR",
            pivot_anchor_id="pivot-anchor-0000000000000000-v1",
            rename_invalid_display_names=False,
            source_views_used=["front.png", "right.png", "back.png", "left.png"],
        )


def test_bounds_center_pivot_cannot_be_combined_with_grounding() -> None:
    """Conflicting target anchors fail before a plan or matrix can be registered."""
    with pytest.raises(ValueError, match="conflicting targets"):
        AgentRepairAssessment(
            assessment_id="assessment-13579bdf13579bdf-v1",
            disposition=AgentDisposition.REPAIR,
            summary="The pickup should rotate around its center while also sitting on the floor.",
            evidence=("The requested anchors have different vertical locations.",),
            confidence=0.9,
            ground_to_y_zero=True,
            pivot_target="BOUNDS_CENTER",
        )


def test_pivot_repair_executes_and_is_independently_verified(tmp_path: Path) -> None:
    """A written candidate is reloaded and its requested pivot anchor is measured at origin."""
    source = tmp_path / "offset-source.glb"
    gltf = load_glb(CLEAN_PATH)
    original_bounds = world_bounds(gltf)
    authored_offset = np.eye(4, dtype=np.float64)
    authored_offset[:3, 3] = [0.4, 0.2, -0.25]
    add_normalization_root(gltf, authored_offset, name="AuthoredOffset")
    save_glb(gltf, source)

    output = tmp_path / "output"
    evidence_root = output.parent / "agent_evidence"
    _write_fake_views(evidence_root / "source_views")
    job = AgentJob(
        source,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()
    observations = job.objective_observations()
    pivot_observation = observations["pivot_observation"]
    assert isinstance(pivot_observation, dict)
    assert pivot_observation["asset_origin_m"] == (0.0, 0.0, 0.0)
    expected_bounds_center = (
        original_bounds.minimum + original_bounds.maximum
    ) / 2.0 + authored_offset[:3, 3]
    expected_footprint_center = (
        expected_bounds_center[0],
        original_bounds.minimum[1] + authored_offset[1, 3],
        expected_bounds_center[2],
    )
    assert pivot_observation["bounds_center_m"] == pytest.approx(expected_bounds_center)
    assert pivot_observation["footprint_center_bottom_m"] == pytest.approx(
        expected_footprint_center
    )
    root_origins = cast(
        tuple[tuple[float, float, float], ...], pivot_observation["root_world_origins_m"]
    )
    assert len(root_origins) == 1
    assert root_origins[0] == pytest.approx((0.4, 0.2, -0.25))
    interpretation = cast(str, pivot_observation["interpretation"])
    assert isinstance(interpretation, str)
    assert "measurements only" in interpretation
    job.register_agent_plan(
        initiating_tool_call_id="pivot-plan-tool-call",
        disposition="REPAIR",
        summary="Center this grounded prop's pivot on the bottom of its footprint.",
        evidence=["The measured footprint center-bottom is offset from the asset origin."],
        confidence=0.96,
        semantic_height_axis=None,
        scale_to_confirmed_height=False,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        pivot_target="FOOTPRINT_CENTER_BOTTOM",
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    job.execute(approved=True, interrupt_id="pivot-approval-v1")
    _write_fake_views(evidence_root / "candidate_views")
    _write_fake_views(evidence_root / "comparison_views")
    job.register_candidate_reassessment(
        initiating_tool_call_id="pivot-reassessment-tool-call",
        candidate_satisfies_assessment=True,
        summary="The candidate preserves the prop and moves its placement anchor as requested.",
        evidence=["Independent candidate views show the same silhouette and grounded placement."],
        confidence=0.95,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
        candidate_views_used=["front.png", "right.png", "back.png", "left.png"],
        comparison_views_used=["front.png", "right.png", "back.png", "left.png"],
    )

    verification, result = job.verify_and_package()

    assert result is not None
    pivot_check = next(
        check for check in verification.checks if check.code == "APPROVED_PIVOT_AT_TARGET"
    )
    assert pivot_check.status.value == "PASS"
    candidate_bounds = world_bounds(load_glb(output / "repaired.glb"))
    assert candidate_bounds.minimum[1] == pytest.approx(0.0, abs=1e-8)
    assert (candidate_bounds.minimum[0] + candidate_bounds.maximum[0]) / 2.0 == pytest.approx(
        0.0, abs=1e-8
    )
    assert (candidate_bounds.minimum[2] + candidate_bounds.maximum[2]) / 2.0 == pytest.approx(
        0.0, abs=1e-8
    )


def test_later_repair_composes_into_proven_normalization_root(tmp_path: Path) -> None:
    """A later repair flattens its delta into the immediately proven Asset Shepherd root."""
    source = tmp_path / "offset-source.glb"
    gltf = load_glb(CLEAN_PATH)
    authored_offset = np.eye(4, dtype=np.float64)
    authored_offset[:3, 3] = [0.4, 0.2, -0.25]
    add_normalization_root(gltf, authored_offset, name="AuthoredOffset")
    save_glb(gltf, source)

    output = tmp_path / "output"
    job = AgentJob(
        source,
        PROFILE_PATH,
        output,
        asset_intent=_intent(height_cm=360.0),
        agent_orchestrated=True,
        max_turns=3,
    )
    evidence_root = output.parent / "agent_evidence"
    job.inspect()
    _write_fake_views(evidence_root / "source_views")
    first_plan = job.register_agent_plan(
        initiating_tool_call_id="first-scale-plan",
        disposition="REPAIR",
        summary="The model is upright; uniformly scale it to the confirmed target height.",
        evidence=["The source Y dimension is semantic height in all four rendered views."],
        confidence=0.96,
        semantic_height_axis="Y",
        scale_to_confirmed_height=True,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    first_payload = next(
        candidate.payload
        for candidate in first_plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )
    assert first_payload.application_mode == "ADD_ROOT"
    job.execute(approved=True, interrupt_id="first-scale-approval")
    _record_successful_candidate_reassessment(job, "first")
    first_verification, first_result = job.verify_and_package()
    assert first_result is not None
    assert first_verification.state.value == "PASSED_PROJECT_READY"
    first_candidate = load_glb(output / "repaired.glb")
    first_node_count = len(first_candidate.nodes)
    assert first_candidate.scenes
    first_scene_roots = first_candidate.scenes[first_candidate.scene or 0].nodes
    assert first_scene_roots
    first_root_index = first_scene_roots[0]
    first_root_matrix = np.asarray(first_payload.proposed_matrix, dtype=np.float64)

    job.begin_next_turn("Place the pivot at the center-bottom of the model footprint.")
    job.inspect()
    _write_fake_views(evidence_root / "source_views")
    second_plan = job.register_agent_plan(
        initiating_tool_call_id="second-pivot-plan",
        disposition="REPAIR",
        summary="Move the placement pivot to the measured footprint center-bottom.",
        evidence=["The measured footprint anchor remains offset from the asset origin."],
        confidence=0.95,
        semantic_height_axis=None,
        scale_to_confirmed_height=False,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        pivot_target="FOOTPRINT_CENTER_BOTTOM",
        rename_invalid_display_names=False,
        source_views_used=["front.png", "right.png", "back.png", "left.png"],
    )
    second_payload = next(
        candidate.payload
        for candidate in second_plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )
    assert second_payload.application_mode == "COMPOSE_EXISTING_ROOT"
    assert second_payload.existing_root_index == first_root_index
    assert np.asarray(second_payload.existing_root_before_matrix) == pytest.approx(
        first_root_matrix
    )
    job.execute(approved=True, interrupt_id="second-pivot-approval")
    _record_successful_candidate_reassessment(job, "second")
    second_verification, second_result = job.verify_and_package()

    assert second_result is not None
    assert second_verification.state.value == "PASSED_PROJECT_READY"
    final_candidate = load_glb(output / "repaired.glb")
    assert len(final_candidate.nodes) == first_node_count
    assert (
        sum(
            1
            for node in final_candidate.nodes
            if (node.name or "").startswith("AssetShepherdNormalization")
        )
        == 1
    )
    assert final_candidate.scenes[final_candidate.scene or 0].nodes == [first_root_index]
    assert np.asarray(second_payload.existing_root_after_matrix) == pytest.approx(
        np.asarray(second_payload.proposed_matrix) @ first_root_matrix
    )
    assert any(
        check.code == "SCENE_ROOT_CHANGE_AUTHORIZED" and check.status.value == "PASS"
        for check in second_verification.checks
    )


def test_render_evidence_rejects_blank_and_clipped_views(tmp_path: Path) -> None:
    """A file's existence cannot satisfy model-visible evidence requirements."""
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        tmp_path / "output",
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    view_root = tmp_path / "views"
    _write_fake_views(view_root)
    views = tuple(view_root / name for name in ("front.png", "right.png", "back.png", "left.png"))
    metrics = job.validate_render_evidence(view_root, views)
    assert set(cast(dict[str, object], metrics["views"])) == {
        "front.png",
        "right.png",
        "back.png",
        "left.png",
    }

    blank_mask = Image.new("L", (160, 160), 0)
    blank_mask.save(view_root / "front.mask.png", format="PNG")
    with pytest.raises(AgentWorkflowError, match="asset is not visible"):
        job.validate_render_evidence(view_root, views)

    clipped_mask = Image.new("L", (160, 160), 0)
    ImageDraw.Draw(clipped_mask).rectangle((0, 20, 100, 140), fill=255)
    clipped_mask.save(view_root / "front.mask.png", format="PNG")
    with pytest.raises(AgentWorkflowError, match="asset is clipped"):
        job.validate_render_evidence(view_root, views)


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


def test_yaw_decision_requires_all_coordinate_labeled_views(tmp_path: Path) -> None:
    """A model cannot authorize yaw from one ambiguous projection."""
    output = tmp_path / "output"
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()
    _write_fake_views(output.parent / "agent_evidence" / "source_views")

    with pytest.raises(AgentWorkflowError, match="all four coordinate-labeled"):
        job.register_agent_plan(
            initiating_tool_call_id="yaw-tool-call",
            disposition="REPAIR",
            summary="The visible front faces source +X instead of glTF source +Z.",
            evidence=["The face and gaze direction are visible in the right view."],
            confidence=0.9,
            semantic_height_axis="Y",
            scale_to_confirmed_height=False,
            rotation_axis="Y",
            rotation_degrees=-90,
            ground_to_y_zero=False,
            rename_invalid_display_names=False,
            source_views_used=["right.png"],
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
        max_turns=2,
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
    _write_fake_views(evidence_root / "comparison_views")
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

    record = job.begin_next_turn("The feet still look too far above the intended contact plane.")
    archived_output = output.parent / "turns" / "turn-000" / "output"
    assert record.turn_index == 0
    assert archived_output.is_dir()
    assert (archived_output / "result.zip").is_file()
    assert job.turn_index == 1
    assert job.turns_remaining == 0
    assert job.source == (archived_output / "repaired.glb").resolve()
    assert job.inspection is None
    assert not output.exists()
    assert not evidence_root.exists()
    assert (output.parent / "turns" / "turn-000" / "agent_evidence").is_dir()
    with pytest.raises(AgentWorkflowError, match="turn limit"):
        job.begin_next_turn("Try once more.")

    restored = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    assert restored.max_turns == 2
    assert restored.turn_index == 1
    assert restored.prior_turns == (record,)
    assert restored.source == job.source
    next_inspection = restored.inspect()
    assert next_inspection.package.file_sha256 == record.output_sha256


def test_conversation_loop_is_not_hard_coded_to_a_second_turn(tmp_path: Path) -> None:
    """Any completed candidate may become another turn until the frozen limit is reached."""
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        tmp_path / "output",
        asset_intent=_intent(),
        agent_orchestrated=True,
        max_turns=4,
    )
    _complete_accept_turn(job, "zero")
    first = job.begin_next_turn("Check the latest candidate again with the updated art review.")
    _complete_accept_turn(job, "one")
    second = job.begin_next_turn("One more review pass is needed for the intended placement.")
    _complete_accept_turn(job, "two")

    assert (first.turn_index, second.turn_index) == (0, 1)
    assert job.turn_index == 2
    assert job.turns_remaining == 1
    assert tuple(turn.turn_index for turn in job.prior_turns) == (0, 1)
    assert job.provenance is not None
    assert job.provenance.conversation_turn_index == 2
    assert job.provenance.prior_turns == job.prior_turns

    job.record_user_acceptance()
    assert job.accepted is True
    with pytest.raises(AgentWorkflowError, match="already accepted"):
        job.begin_next_turn("Attempt to reopen a completed conversation.")

    restored = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        tmp_path / "output",
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    assert restored.accepted is True


def test_refinement_can_rework_the_current_iteration_instead_of_promoting_candidate(
    tmp_path: Path,
) -> None:
    """The explicit survivor choice is durable even when the user selects the turn input."""
    output = tmp_path / "output"
    job = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
        max_turns=3,
    )
    _complete_accept_turn(job, "input-choice")

    record = job.begin_next_turn(
        "Reconsider the current iteration with a different pivot.",
        continuation_source="INPUT",
    )

    assert record.continuation_source == "INPUT"
    assert record.next_source_sha256 == record.source_sha256
    assert job.source == CLEAN_PATH.resolve()
    restored = AgentJob(
        CLEAN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    assert restored.source == CLEAN_PATH.resolve()
    assert restored.prior_turns == (record,)


def test_display_name_only_action_packages_without_visual_reassessment(tmp_path: Path) -> None:
    """Index-preserving names use exact inventory checks instead of a fake visual gate."""
    output = tmp_path / "output"
    job = AgentJob(
        BROKEN_PATH,
        PROFILE_PATH,
        output,
        asset_intent=_intent(),
        agent_orchestrated=True,
    )
    job.inspect()
    job.register_agent_plan(
        initiating_tool_call_id="names-only-plan-tool-call",
        disposition="REPAIR",
        summary="Keep the physical asset unchanged and repair only invalid display names.",
        evidence=["Inspection found invalid and duplicate node and mesh display names."],
        confidence=0.98,
        semantic_height_axis="Y",
        scale_to_confirmed_height=False,
        rotation_axis=None,
        rotation_degrees=0,
        ground_to_y_zero=False,
        rename_invalid_display_names=True,
        source_views_used=[],
    )
    outcome = job.execute(approved=None, interrupt_id=None)

    assert outcome.executed_action_ids
    assert all(action_id.startswith("rename-") for action_id in outcome.executed_action_ids)
    verification, result = job.verify_and_package()

    assert result is not None
    assert job.candidate_reassessment is None
    assert all(check.code != "AGENT_VISUAL_REASSESSMENT" for check in verification.checks)
    assert (output / "result.zip").is_file()
