"""Authorization validation and deterministic GLB repair application."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import numpy as np

from asset_shepherd.glb import add_normalization_root, load_glb, save_glb
from asset_shepherd.models import (
    DecisionRecord,
    Decisions,
    DecisionSource,
    DecisionValue,
    NormalizationPayload,
    RenamePayload,
    RepairKind,
    RepairPlan,
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
            existing_names = {node.name for node in gltf.nodes if node.name}
            add_normalization_root(
                gltf,
                matrix,
                name=_normalization_name(existing_names),
            )
        else:
            raise RepairInvariantError(f"Unregistered repair kind: {candidate.kind}")
        executed.append(candidate.id)
    save_glb(gltf, output)
    if sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RepairInvariantError("Source changed during repair")
    output_hash = sha256(output.read_bytes()).hexdigest()
    return RepairOutcome(
        source_sha256=source_hash,
        output_sha256=output_hash,
        executed_action_ids=tuple(executed),
        rejected_action_ids=tuple(rejected),
    )
