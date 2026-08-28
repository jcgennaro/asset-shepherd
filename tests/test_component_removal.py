"""Bounded disconnected-component inventory and removal acceptance tests."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportPrivateUsage=false

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    FLOAT,
    GLTF2,
    SCALAR,
    UNSIGNED_SHORT,
    VEC3,
    Accessor,
    Asset,
    Attributes,
    Buffer,
    BufferView,
    Mesh,
    Node,
    Primitive,
    Scene,
)

from asset_shepherd.agent_job import AgentJob
from asset_shepherd.fixtures import fixture_profile
from asset_shepherd.glb import load_glb, save_glb, world_bounds
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentDisposition,
    AgentRepairAssessment,
    ComponentRemovalPayload,
    ProposalDisposition,
    ProposalLane,
    ProposalResponse,
)
from asset_shepherd.planner import plan_agent_repairs
from asset_shepherd.repair import apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.web import _inspection_checks, _source_scene
from asset_shepherd.workflow import build_provenance

_TETRAHEDRON_INDICES = np.asarray(
    [0, 2, 1, 0, 1, 3, 1, 2, 3, 2, 0, 3],
    dtype=np.uint16,
)


def _write_components(path: Path, offsets: tuple[tuple[float, float, float], ...]) -> None:
    base = np.asarray(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        dtype=np.float32,
    )
    positions = np.concatenate([base + np.asarray(offset, dtype=np.float32) for offset in offsets])
    indices = np.concatenate(
        [_TETRAHEDRON_INDICES + (4 * index) for index in range(len(offsets))]
    ).astype(np.uint16)
    position_bytes = positions.tobytes()
    padding = b"\0" * ((4 - len(position_bytes) % 4) % 4)
    blob = position_bytes + padding + indices.tobytes()
    gltf = GLTF2(
        asset=Asset(version="2.0", generator="Asset Shepherd component test"),
        scene=0,
        scenes=[Scene(name="Scene", nodes=[0])],
        nodes=[Node(name="ComponentSet", mesh=0)],
        meshes=[
            Mesh(
                name="ComponentSetMesh",
                primitives=[Primitive(attributes=Attributes(POSITION=0), indices=1)],
            )
        ],
        accessors=[
            Accessor(
                bufferView=0,
                componentType=FLOAT,
                count=len(positions),
                type=VEC3,
                min=positions.min(axis=0).tolist(),
                max=positions.max(axis=0).tolist(),
            ),
            Accessor(
                bufferView=1,
                componentType=UNSIGNED_SHORT,
                count=len(indices),
                type=SCALAR,
                min=[int(indices.min())],
                max=[int(indices.max())],
            ),
        ],
        bufferViews=[
            BufferView(
                buffer=0,
                byteOffset=0,
                byteLength=len(position_bytes),
                target=ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=len(position_bytes) + len(padding),
                byteLength=indices.nbytes,
                target=ELEMENT_ARRAY_BUFFER,
            ),
        ],
        buffers=[Buffer(byteLength=len(blob))],
    )
    gltf.set_binary_blob(blob)
    save_glb(gltf, path)


def _assessment(component_ids: tuple[str, ...]) -> AgentRepairAssessment:
    return AgentRepairAssessment(
        assessment_id="assessment-0123456789abcdef-v1",
        disposition=AgentDisposition.REPAIR,
        summary="Two clearly duplicated disconnected bodies should be removed after review.",
        evidence=("All four source views show one intended body and two duplicate copies.",),
        confidence=1.0,
        remove_component_ids=component_ids,
        source_views_used=("front", "side", "three_quarter", "top"),
    )


def test_exact_components_can_be_approved_removed_and_verified(tmp_path: Path) -> None:
    """Only the two exact selected bodies disappear; the retained body stays byte-equivalent."""
    source = tmp_path / "source.glb"
    candidate = tmp_path / "candidate.glb"
    _write_components(source, ((0, 0, 0), (3, 0, 0), (6, 0, 0)))
    profile = fixture_profile()
    original = inspect_asset(source, profile)
    assert original.diagnostics is not None
    primitive = original.diagnostics.primitives[0]
    assert primitive.virtual_weld_connected_component_count == 3
    assert len(primitive.disconnected_components) == 3
    assert primitive.component_removal_safe
    removed_ids = tuple(
        component.component_id for component in primitive.disconnected_components[1:]
    )

    assessment = _assessment(removed_ids)
    plan = plan_agent_repairs(
        original,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    payload = next(
        repair.payload
        for repair in plan.candidates
        if isinstance(repair.payload, ComponentRemovalPayload)
    )
    assert payload.primitives[0].removed_triangle_count == 8
    assert payload.primitives[0].after_triangle_count == 4
    assert plan.approval_action_ids == ("remove-disconnected-components-v1",)

    job = AgentJob(
        source=source,
        profile_path=Path("profiles/unreal_indie_robot.json"),
        output_dir=tmp_path / "job",
        agent_orchestrated=True,
    )
    job.inspection = original
    job.agent_assessment = assessment
    job.selected_plan = plan
    topology = _inspection_checks(job)[2]
    assert topology.response_lane is None
    assert len(topology.component_proposals) == 3
    assert sum(item.proposed_removal for item in topology.component_proposals) == 2
    source_scene = _source_scene(source, original)
    assert len(source_scene.component_boxes) == 3

    decided_at = datetime(2026, 8, 27, tzinfo=UTC)
    decisions = create_decisions(
        plan,
        {"remove-disconnected-components-v1": True},
        decided_at=decided_at,
    )
    outcome = apply_repairs(source, candidate, plan, decisions)
    provenance = build_provenance(
        profile,
        plan,
        decisions,
        outcome,
        started_at=decided_at,
        completed_at=decided_at,
        agent_assessment=assessment,
    )
    verification = verify_repair(
        source,
        candidate,
        profile,
        original,
        plan,
        decisions,
        outcome,
        provenance,
    )
    repaired = inspect_asset(candidate, profile)
    repaired_bounds = world_bounds(load_glb(candidate))

    assert repaired.geometry is not None
    assert repaired.geometry.triangle_count == 4
    assert repaired.geometry.vertex_count == 12
    assert repaired_bounds.minimum.tolist() == [0.0, 0.0, 0.0]
    assert repaired_bounds.maximum.tolist() == [1.0, 1.0, 1.0]
    assert repaired.diagnostics is not None
    repaired_primitive = repaired.diagnostics.primitives[0]
    assert repaired_primitive.virtual_weld_connected_component_count == 1
    assert repaired_primitive.unused_position_count == 8
    confirmation = next(
        check
        for check in verification.checks
        if check.code == "DISCONNECTED_COMPONENT_REMOVAL_CONFIRMED"
    )
    assert confirmation.status == "PASS"
    assert all(check.status != "FAIL" for check in verification.checks), [
        (check.code, check.expected, check.actual)
        for check in verification.checks
        if check.status == "FAIL"
    ]


def test_component_specific_feedback_reopens_planning_without_mutation(tmp_path: Path) -> None:
    """A user can keep one proposed body and ask to remove a different retained body."""
    source = tmp_path / "source.glb"
    _write_components(source, ((0, 0, 0), (3, 0, 0), (6, 0, 0)))
    profile = fixture_profile()
    inspection = inspect_asset(source, profile)
    assert inspection.diagnostics is not None
    component_ids = tuple(
        component.component_id
        for component in inspection.diagnostics.primitives[0].disconnected_components
    )
    assessment = _assessment((component_ids[1],))
    plan = plan_agent_repairs(
        inspection,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    job = AgentJob(
        source=source,
        profile_path=Path("profiles/unreal_indie_robot.json"),
        output_dir=tmp_path / "job",
        agent_orchestrated=True,
    )
    job.inspection = inspection
    job.agent_assessment = assessment
    job.selected_plan = plan
    job.output_dir.mkdir(parents=True)
    (job.output_dir / "repair_plan.json").write_text(
        plan.model_dump_json(indent=2), encoding="utf-8"
    )
    job.agent_assessment_path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")
    job.set_pending_interrupt("component-plan-feedback-v1")
    responses = (
        ProposalResponse(
            lane=ProposalLane.TOPOLOGY,
            component_id=component_ids[1],
            disposition=ProposalDisposition.REJECT,
        ),
        ProposalResponse(
            lane=ProposalLane.TOPOLOGY,
            component_id=component_ids[2],
            disposition=ProposalDisposition.COMMENT,
            comment="Remove this currently retained component in the revised plan.",
        ),
    )

    assert job.request_plan_revision(responses) == responses
    assert job.selected_plan is None
    assert job.outcome is None
    assert not (tmp_path / "job" / "candidate.glb").exists()


def test_rejected_component_selection_preserves_all_geometry(tmp_path: Path) -> None:
    """Rejecting the exact selection records the decision and executes no component filter."""
    source = tmp_path / "source.glb"
    candidate = tmp_path / "candidate.glb"
    _write_components(source, ((0, 0, 0), (3, 0, 0), (6, 0, 0)))
    source_before = source.read_bytes()
    profile = fixture_profile()
    inspection = inspect_asset(source, profile)
    assert inspection.diagnostics is not None
    removed_ids = tuple(
        component.component_id
        for component in inspection.diagnostics.primitives[0].disconnected_components[1:]
    )
    plan = plan_agent_repairs(
        inspection,
        profile,
        _assessment(removed_ids),
        confirmed_target_height_m=1.0,
    )
    decisions = create_decisions(
        plan,
        {"remove-disconnected-components-v1": False},
        decided_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    outcome = apply_repairs(source, candidate, plan, decisions)
    rejected = next(
        record
        for record in decisions.records
        if record.candidate_id == "remove-disconnected-components-v1"
    )
    result = inspect_asset(candidate, profile)

    assert rejected.decision == "REJECTED"
    assert "remove-disconnected-components-v1" not in outcome.executed_action_ids
    assert source.read_bytes() == source_before
    assert result.geometry is not None
    assert result.geometry.triangle_count == 12
    assert result.diagnostics is not None
    assert len(result.diagnostics.primitives[0].disconnected_components) == 3


def test_near_contact_backoff_groups_bodies_without_authorizing_mutation(tmp_path: Path) -> None:
    """Small gaps change advisory groups, never exact IDs or mutation authority."""
    source = tmp_path / "near.glb"
    _write_components(source, ((0, 0, 0), (1.0005, 0, 0)))
    inspection = inspect_asset(source, fixture_profile())
    assert inspection.diagnostics is not None
    primitive = inspection.diagnostics.primitives[0]

    assert primitive.virtual_weld_connected_component_count == 2
    assert len(primitive.disconnected_components) == 2
    assert primitive.near_contact_probes[0].group_count == 2
    assert primitive.near_contact_probes[-1].group_count == 1
    assert {component.near_contact_group for component in primitive.disconnected_components} == {0}
    next(
        finding
        for finding in inspection.findings
        if finding.code == "DISCONNECTED_COMPONENTS_DETECTED"
    )
    report_only = AgentRepairAssessment(
        assessment_id="assessment-fedcba9876543210-v1",
        disposition=AgentDisposition.REPORT_ONLY,
        summary="The nearby bodies may be intentional, so no deletion is justified.",
        evidence=("Near-contact grouping is advisory and does not establish semantics.",),
        confidence=0.8,
    )
    plan = plan_agent_repairs(
        inspection,
        fixture_profile(),
        report_only,
        confirmed_target_height_m=1.0,
    )
    assert not any(
        isinstance(repair.payload, ComponentRemovalPayload) for repair in plan.candidates
    )


def test_component_plan_refuses_unknown_or_total_removal(tmp_path: Path) -> None:
    """Stable inventory IDs bind authorization and at least one body must survive."""
    source = tmp_path / "source.glb"
    _write_components(source, ((0, 0, 0), (3, 0, 0)))
    profile = fixture_profile()
    inspection = inspect_asset(source, profile)
    assert inspection.diagnostics is not None
    component_ids = tuple(
        component.component_id
        for component in inspection.diagnostics.primitives[0].disconnected_components
    )

    try:
        plan_agent_repairs(
            inspection,
            profile,
            _assessment(("component-m999-p999-c999-unknown",)),
            confirmed_target_height_m=1.0,
        )
    except ValueError as error:
        assert "unknown IDs" in str(error)
    else:
        raise AssertionError("Unknown component ID was accepted")

    try:
        plan_agent_repairs(
            inspection,
            profile,
            _assessment(component_ids),
            confirmed_target_height_m=1.0,
        )
    except ValueError as error:
        assert "every component" in str(error)
    else:
        raise AssertionError("Total component removal was accepted")
