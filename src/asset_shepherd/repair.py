"""Authorization validation and deterministic GLB repair application."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np

from asset_shepherd.glb import (
    GlbError,
    add_normalization_root,
    clean_degenerate_geometry,
    load_glb,
    node_local_matrix,
    raw_glb_document,
    save_glb,
    weld_identical_vertex_tuples,
)
from asset_shepherd.models import (
    DecisionRecord,
    Decisions,
    DecisionSource,
    DecisionValue,
    DegenerateGeometryPayload,
    NormalizationPayload,
    RenamePayload,
    RepairKind,
    RepairPlan,
    WeldPayload,
)


class RepairAuthorizationError(ValueError):
    """Raised when repair decisions do not authorize the exact plan."""


class RepairInvariantError(ValueError):
    """Raised when a repair would violate a deterministic safety invariant."""


@dataclass(frozen=True)
class RepairOutcome:
    """Hashes and actions produced by one repair execution."""

    source_sha256: str
    output_sha256: str
    executed_action_ids: tuple[str, ...]
    rejected_action_ids: tuple[str, ...]


def create_decisions(
    plan: RepairPlan,
    approvals: dict[str, bool],
    *,
    decided_at: datetime,
    source: DecisionSource = DecisionSource.USER_APPROVAL_FILE,
) -> Decisions:
    """Create a complete decision artifact from policy and explicit user choices."""
    expected_approvals = set(plan.approval_action_ids)
    supplied = set(approvals)
    if supplied != expected_approvals:
        missing = sorted(expected_approvals - supplied)
        unknown = sorted(supplied - expected_approvals)
        raise RepairAuthorizationError(
            f"Approval choices do not match the plan; missing={missing}, unknown={unknown}"
        )
    records = [
        DecisionRecord(
            candidate_id=candidate_id,
            decision=DecisionValue.AUTO_AUTHORIZED,
            source=DecisionSource.POLICY,
            decided_at=decided_at,
        )
        for candidate_id in plan.auto_action_ids
    ]
    records.extend(
        DecisionRecord(
            candidate_id=candidate_id,
            decision=DecisionValue.APPROVED if approvals[candidate_id] else DecisionValue.REJECTED,
            source=source,
            decided_at=decided_at,
        )
        for candidate_id in plan.approval_action_ids
    )
    decisions = Decisions(plan_id=plan.plan_id, records=tuple(records))
    validate_decisions(plan, decisions)
    return decisions


def validate_decisions(plan: RepairPlan, decisions: Decisions) -> None:
    """Reject missing, duplicate, unknown, or policy-inconsistent decisions."""
    if plan.blocked:
        raise RepairAuthorizationError("A blocked repair plan cannot be authorized")
    if decisions.plan_id != plan.plan_id:
        raise RepairAuthorizationError("Decision artifact references a different plan")
    candidate_ids = {candidate.id for candidate in plan.candidates}
    record_ids = [record.candidate_id for record in decisions.records]
    if len(record_ids) != len(set(record_ids)):
        raise RepairAuthorizationError("Decision artifact contains duplicate candidate IDs")
    unknown = set(record_ids) - candidate_ids
    if unknown:
        raise RepairAuthorizationError(f"Decision artifact contains unknown candidates: {unknown}")
    records = {record.candidate_id: record for record in decisions.records}
    for candidate_id in plan.auto_action_ids:
        record = records.get(candidate_id)
        if record is None:
            raise RepairAuthorizationError(f"Missing policy decision for {candidate_id}")
        if (
            record.decision is not DecisionValue.AUTO_AUTHORIZED
            or record.source is not DecisionSource.POLICY
        ):
            raise RepairAuthorizationError(f"Invalid policy authorization for {candidate_id}")
    for candidate_id in plan.approval_action_ids:
        record = records.get(candidate_id)
        if record is None:
            raise RepairAuthorizationError(f"Missing user decision for {candidate_id}")
        if record.decision not in {DecisionValue.APPROVED, DecisionValue.REJECTED}:
            raise RepairAuthorizationError(f"Invalid user decision for {candidate_id}")
        if record.source is DecisionSource.POLICY:
            raise RepairAuthorizationError(f"User approval cannot come from policy: {candidate_id}")


def _normalization_name(existing_names: set[str]) -> str:
    name = "AssetShepherdNormalization"
    suffix = 1
    while name in existing_names:
        name = f"AssetShepherdNormalization_{suffix:02d}"
        suffix += 1
    return name


def apply_repairs(
    source: Path,
    output: Path,
    plan: RepairPlan,
    decisions: Decisions,
) -> RepairOutcome:
    """Apply authorized repairs to a new GLB while preserving the source."""
    validate_decisions(plan, decisions)
    if source.resolve() == output.resolve():
        raise RepairInvariantError("Repair output must not overwrite the source")
    source_bytes = source.read_bytes()
    source_hash = sha256(source_bytes).hexdigest()
    if source_hash != plan.source_sha256:
        raise RepairInvariantError("Source hash no longer matches the repair plan")
    gltf = load_glb(source)
    records = {record.candidate_id: record for record in decisions.records}
    executed: list[str] = []
    rejected: list[str] = []
    for candidate in plan.candidates:
        record = records[candidate.id]
        if record.decision is DecisionValue.REJECTED:
            rejected.append(candidate.id)
            continue
        if candidate.kind in {RepairKind.RENAME_NODE, RepairKind.RENAME_MESH}:
            payload = candidate.payload
            if not isinstance(payload, RenamePayload):
                raise RepairInvariantError("Rename candidate has the wrong payload")
            if payload.component_type == "node":
                if not 0 <= payload.component_index < len(gltf.nodes):
                    raise RepairInvariantError("Rename references an invalid node")
                if gltf.nodes[payload.component_index].name != payload.before_name:
                    raise RepairInvariantError("Node name no longer matches the repair plan")
                gltf.nodes[payload.component_index].name = payload.after_name
            else:
                if not 0 <= payload.component_index < len(gltf.meshes):
                    raise RepairInvariantError("Rename references an invalid mesh")
                if gltf.meshes[payload.component_index].name != payload.before_name:
                    raise RepairInvariantError("Mesh name no longer matches the repair plan")
                gltf.meshes[payload.component_index].name = payload.after_name
        elif candidate.kind is RepairKind.NORMALIZATION_TRANSFORM:
            payload = candidate.payload
            if not isinstance(payload, NormalizationPayload):
                raise RepairInvariantError("Normalization candidate has the wrong payload")
            matrix = np.asarray(payload.proposed_matrix, dtype=np.float64)
            if payload.application_mode == "COMPOSE_EXISTING_ROOT":
                root_index = payload.existing_root_index
                before_matrix = payload.existing_root_before_matrix
                after_matrix = payload.existing_root_after_matrix
                if root_index is None or before_matrix is None or after_matrix is None:
                    raise RepairInvariantError(
                        "Composed normalization is missing its root contract"
                    )
                if not 0 <= root_index < len(gltf.nodes):
                    raise RepairInvariantError("Composed normalization references an invalid root")
                scene_index = gltf.scene or 0
                if not 0 <= scene_index < len(gltf.scenes) or tuple(
                    gltf.scenes[scene_index].nodes or ()
                ) != (root_index,):
                    raise RepairInvariantError(
                        "Composed normalization root is no longer the active scene root"
                    )
                root = gltf.nodes[root_index]
                if not (root.name or "").startswith("AssetShepherdNormalization"):
                    raise RepairInvariantError("Composed normalization root identity changed")
                current = node_local_matrix(root)
                expected_before = np.asarray(before_matrix, dtype=np.float64)
                expected_after = np.asarray(after_matrix, dtype=np.float64)
                if not np.allclose(current, expected_before, rtol=0.0, atol=1e-12):
                    raise RepairInvariantError("Composed normalization root matrix changed")
                if not np.allclose(
                    expected_after,
                    matrix @ expected_before,
                    rtol=0.0,
                    atol=1e-12,
                ):
                    raise RepairInvariantError("Composed normalization matrix is inconsistent")
                root.matrix = expected_after.T.reshape(-1).tolist()
                root.translation = None
                root.rotation = None
                root.scale = None
            else:
                existing_names = {node.name for node in gltf.nodes if node.name}
                add_normalization_root(
                    gltf,
                    matrix,
                    name=_normalization_name(existing_names),
                )
        elif candidate.kind is RepairKind.WELD_IDENTICAL_VERTICES:
            payload = candidate.payload
            if not isinstance(payload, WeldPayload):
                raise RepairInvariantError("Vertex weld candidate has the wrong payload")
            expected_merges = {
                (primitive.mesh_index, primitive.primitive_index): primitive.merge_count
                for primitive in payload.primitives
            }
            try:
                raw_document = raw_glb_document(source)
                raw_meshes_value = raw_document.get("meshes")
                if not isinstance(raw_meshes_value, list):
                    raise GlbError("Weld source has no raw mesh records")
                raw_meshes = cast(list[object], raw_meshes_value)
                for primitive_payload in payload.primitives:
                    raw_mesh_value = raw_meshes[primitive_payload.mesh_index]
                    if not isinstance(raw_mesh_value, dict):
                        raise GlbError("Weld source mesh record is invalid")
                    raw_mesh = cast(dict[str, object], raw_mesh_value)
                    raw_primitives_value = raw_mesh.get("primitives")
                    if not isinstance(raw_primitives_value, list):
                        raise GlbError("Weld source has no raw primitive records")
                    raw_primitives = cast(list[object], raw_primitives_value)
                    raw_primitive_value = raw_primitives[primitive_payload.primitive_index]
                    if not isinstance(raw_primitive_value, dict):
                        raise GlbError("Weld source primitive record is invalid")
                    raw_primitive = cast(dict[str, object], raw_primitive_value)
                    raw_attributes_value = raw_primitive.get("attributes")
                    if not isinstance(raw_attributes_value, dict):
                        raise GlbError("Weld source attributes are invalid")
                    raw_attributes = cast(dict[str, object], raw_attributes_value)
                    parsed_primitive = gltf.meshes[primitive_payload.mesh_index].primitives[
                        primitive_payload.primitive_index
                    ]
                    parsed_semantics = {
                        semantic
                        for semantic, accessor_index in vars(parsed_primitive.attributes).items()
                        if isinstance(accessor_index, int)
                    }
                    if set(raw_attributes) != parsed_semantics:
                        raise GlbError(
                            "Weld refuses vertex attributes that the GLB adapter cannot preserve"
                        )
                weld_identical_vertex_tuples(gltf, expected_merges)
            except GlbError as error:
                raise RepairInvariantError(str(error)) from error
        elif candidate.kind is RepairKind.CLEAN_DEGENERATE_GEOMETRY:
            payload = candidate.payload
            if not isinstance(payload, DegenerateGeometryPayload):
                raise RepairInvariantError("Degenerate cleanup candidate has the wrong payload")
            expected_removals = {
                (primitive.mesh_index, primitive.primitive_index): (
                    primitive.removed_degenerate_triangle_count,
                    primitive.removed_unused_position_count,
                )
                for primitive in payload.primitives
            }
            try:
                raw_document = raw_glb_document(source)
                raw_meshes_value = raw_document.get("meshes")
                if not isinstance(raw_meshes_value, list):
                    raise GlbError("Geometry cleanup source has no raw mesh records")
                raw_meshes = cast(list[object], raw_meshes_value)
                for primitive_payload in payload.primitives:
                    raw_mesh_value = raw_meshes[primitive_payload.mesh_index]
                    if not isinstance(raw_mesh_value, dict):
                        raise GlbError("Geometry cleanup source mesh record is invalid")
                    raw_primitives_value = cast(dict[str, object], raw_mesh_value).get("primitives")
                    if not isinstance(raw_primitives_value, list):
                        raise GlbError("Geometry cleanup source has no raw primitive records")
                    raw_primitives = cast(list[object], raw_primitives_value)
                    raw_primitive_value = raw_primitives[primitive_payload.primitive_index]
                    if not isinstance(raw_primitive_value, dict):
                        raise GlbError("Geometry cleanup source primitive record is invalid")
                    raw_primitive = cast(dict[str, object], raw_primitive_value)
                    raw_attributes_value = raw_primitive.get("attributes")
                    if not isinstance(raw_attributes_value, dict):
                        raise GlbError("Geometry cleanup source attributes are invalid")
                    parsed_primitive = gltf.meshes[primitive_payload.mesh_index].primitives[
                        primitive_payload.primitive_index
                    ]
                    parsed_semantics = {
                        semantic
                        for semantic, accessor_index in vars(parsed_primitive.attributes).items()
                        if isinstance(accessor_index, int)
                    }
                    raw_attributes = cast(dict[str, object], raw_attributes_value)
                    if set(raw_attributes) != parsed_semantics:
                        raise GlbError(
                            "Geometry cleanup refuses vertex attributes that the GLB adapter "
                            "cannot preserve"
                        )
                clean_degenerate_geometry(gltf, expected_removals)
            except (GlbError, IndexError) as error:
                raise RepairInvariantError(str(error)) from error
        else:
            raise RepairInvariantError(f"Unregistered repair kind: {candidate.kind}")
        executed.append(candidate.id)
    if executed:
        save_glb(gltf, output)
    else:
        output.write_bytes(source_bytes)
    if sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RepairInvariantError("Source changed during repair")
    output_hash = sha256(output.read_bytes()).hexdigest()
    return RepairOutcome(
        source_sha256=source_hash,
        output_sha256=output_hash,
        executed_action_ids=tuple(executed),
        rejected_action_ids=tuple(rejected),
    )
