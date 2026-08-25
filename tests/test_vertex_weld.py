"""Attribute-safe vertex-tuple welding acceptance tests."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

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
    VEC2,
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

from asset_shepherd.fixtures import fixture_profile
from asset_shepherd.glb import save_glb
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import AgentDisposition, AgentRepairAssessment, WeldPayload
from asset_shepherd.planner import plan_agent_repairs
from asset_shepherd.repair import apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.workflow import build_provenance


def _write_safe_duplicate_fixture(path: Path) -> None:
    positions = np.asarray(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0], [1, 1, 0]],
        dtype=np.float32,
    )
    normals = np.tile(np.asarray([[0, 0, 1]], dtype=np.float32), (5, 1))
    texcoords = np.asarray(
        [[0, 0], [1, 0], [0, 1], [0, 0], [1, 1]],
        dtype=np.float32,
    )
    indices = np.asarray([0, 1, 2, 3, 2, 4], dtype=np.uint16)
    arrays = (positions, normals, texcoords, indices)
    targets = (ARRAY_BUFFER, ARRAY_BUFFER, ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER)
    blob = bytearray()
    views: list[BufferView] = []
    for values, target in zip(arrays, targets, strict=True):
        while len(blob) % 4:
            blob.append(0)
        views.append(
            BufferView(
                buffer=0,
                byteOffset=len(blob),
                byteLength=values.nbytes,
                target=target,
            )
        )
        blob.extend(values.tobytes())
    accessors = [
        Accessor(
            bufferView=0,
            componentType=FLOAT,
            count=len(positions),
            type=VEC3,
            min=positions.min(axis=0).tolist(),
            max=positions.max(axis=0).tolist(),
        ),
        Accessor(bufferView=1, componentType=FLOAT, count=len(normals), type=VEC3),
        Accessor(bufferView=2, componentType=FLOAT, count=len(texcoords), type=VEC2),
        Accessor(
            bufferView=3,
            componentType=UNSIGNED_SHORT,
            count=len(indices),
            type=SCALAR,
            min=[int(indices.min())],
            max=[int(indices.max())],
        ),
    ]
    gltf = GLTF2(
        asset=Asset(version="2.0", generator="Asset Shepherd weld test"),
        scene=0,
        scenes=[Scene(name="Scene", nodes=[0])],
        nodes=[Node(name="SafeDuplicate", mesh=0)],
        meshes=[
            Mesh(
                name="SafeDuplicateMesh",
                primitives=[
                    Primitive(
                        attributes=Attributes(POSITION=0, NORMAL=1, TEXCOORD_0=2),
                        indices=3,
                    )
                ],
            )
        ],
        accessors=accessors,
        bufferViews=views,
        buffers=[Buffer(byteLength=len(blob))],
    )
    gltf.set_binary_blob(bytes(blob))
    save_glb(gltf, path)


def test_agent_requested_safe_weld_executes_and_verifies(tmp_path: Path) -> None:
    """The tool compacts identical tuples while independent corner evidence remains unchanged."""
    source = tmp_path / "source.glb"
    candidate = tmp_path / "candidate.glb"
    _write_safe_duplicate_fixture(source)
    profile = fixture_profile()
    original = inspect_asset(source, profile)
    assert original.diagnostics is not None
    primitive = original.diagnostics.primitives[0]
    assert primitive.duplicate_position_count == 1
    assert primitive.attribute_safe_merge_count == 1

    assessment = AgentRepairAssessment(
        assessment_id="assessment-0123456789abcdef-v1",
        disposition=AgentDisposition.REPAIR,
        summary="One redundant complete vertex tuple can be compacted without crossing a seam.",
        evidence=("Inspection reports one attribute-safe merge and no protected duplicate.",),
        confidence=1.0,
        weld_identical_vertices=True,
    )
    plan = plan_agent_repairs(
        original,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    weld = next(
        candidate_repair.payload
        for candidate_repair in plan.candidates
        if isinstance(candidate_repair.payload, WeldPayload)
    )
    assert weld.primitives[0].merge_count == 1
    assert plan.auto_action_ids == ("weld-identical-vertices-v1",)

    decided_at = datetime(2026, 8, 24, tzinfo=UTC)
    decisions = create_decisions(plan, {}, decided_at=decided_at)
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
    output = inspect_asset(candidate, profile)

    assert output.geometry is not None
    assert output.geometry.vertex_count == 4
    assert output.geometry.triangle_count == 2
    assert output.diagnostics is not None
    assert output.diagnostics.primitives[0].attribute_safe_merge_count == 0
    assert all(check.status != "FAIL" for check in verification.checks)


def test_chip_uv_seams_are_detected_but_not_registered_as_safe_weld() -> None:
    """The real chip's 5,312 coincident positions remain protected by its UV tuples."""
    chip = Path("build/user-deliverables/computer-chip-candidate.glb")
    if not chip.is_file():
        return
    inspection = inspect_asset(chip, fixture_profile())
    assert inspection.diagnostics is not None
    primitive = inspection.diagnostics.primitives[0]

    assert primitive.duplicate_position_count == 5312
    assert primitive.virtual_weld_boundary_edge_count == 91
    assert primitive.virtual_weld_non_manifold_edge_count == 50
    assert primitive.attribute_safe_merge_count == 0
    assert primitive.protected_duplicate_count == 5312
    assert primitive.protected_attribute_conflicts == ("TEXCOORD_0",)
