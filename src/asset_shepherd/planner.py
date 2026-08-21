"""Deterministic version-1 candidate repair planning."""

from itertools import product
from typing import Literal

import numpy as np

from asset_shepherd.models import (
    ActionClass,
    Bounds3D,
    CandidateRepair,
    InspectionResult,
    Matrix4,
    NormalizationComponent,
    NormalizationPayload,
    ProjectProfile,
    RenamePayload,
    RepairEligibility,
    RepairKind,
    RepairPlan,
)

_NORMALIZATION_CODES = {
    "HEIGHT_OUT_OF_RANGE": "scale",
    "ORIENTATION_NOT_Y_UP": "orientation",
    "NOT_GROUNDED": "grounding",
}


def _bounds_from_points(points: np.ndarray) -> Bounds3D:
    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    dimensions = maximum - minimum
    minimum_m = (float(minimum[0]), float(minimum[1]), float(minimum[2]))
    maximum_m = (float(maximum[0]), float(maximum[1]), float(maximum[2]))
    dimensions_m = (float(dimensions[0]), float(dimensions[1]), float(dimensions[2]))
    return Bounds3D(
        minimum_m=minimum_m,
        maximum_m=maximum_m,
        dimensions_m=dimensions_m,
        minimum_cm=(minimum_m[0] * 100.0, minimum_m[1] * 100.0, minimum_m[2] * 100.0),
        maximum_cm=(maximum_m[0] * 100.0, maximum_m[1] * 100.0, maximum_m[2] * 100.0),
        dimensions_cm=(
            dimensions_m[0] * 100.0,
            dimensions_m[1] * 100.0,
            dimensions_m[2] * 100.0,
        ),
    )


def _matrix_model(matrix: np.ndarray) -> Matrix4:
    return (
        (float(matrix[0, 0]), float(matrix[0, 1]), float(matrix[0, 2]), float(matrix[0, 3])),
        (float(matrix[1, 0]), float(matrix[1, 1]), float(matrix[1, 2]), float(matrix[1, 3])),
        (float(matrix[2, 0]), float(matrix[2, 1]), float(matrix[2, 2]), float(matrix[2, 3])),
        (float(matrix[3, 0]), float(matrix[3, 1]), float(matrix[3, 2]), float(matrix[3, 3])),
    )


def _bounds_corners(bounds: Bounds3D) -> np.ndarray:
    return np.asarray(
        list(
            product(
                (bounds.minimum_m[0], bounds.maximum_m[0]),
                (bounds.minimum_m[1], bounds.maximum_m[1]),
                (bounds.minimum_m[2], bounds.maximum_m[2]),
            )
        ),
        dtype=np.float64,
    )


def _axis_to_positive_y(bounds: Bounds3D, axis: str) -> np.ndarray:
    rotation = np.eye(4, dtype=np.float64)
    axis_index = {"X": 0, "Y": 1, "Z": 2}[axis]
    points_positive = abs(bounds.minimum_m[axis_index]) <= abs(bounds.maximum_m[axis_index])
    if axis == "X":
        direction = 1.0 if points_positive else -1.0
        rotation[:3, :3] = np.asarray(
            [[0.0, -direction, 0.0], [direction, 0.0, 0.0], [0.0, 0.0, 1.0]]
        )
    elif axis == "Z":
        direction = 1.0 if points_positive else -1.0
        rotation[:3, :3] = np.asarray(
            [[1.0, 0.0, 0.0], [0.0, 0.0, direction], [0.0, -direction, 0.0]]
        )
    return rotation


def _normalization_candidate(
    inspection: InspectionResult,
    profile: ProjectProfile,
) -> CandidateRepair | None:
    if inspection.geometry is None:
        return None
    relevant = [finding for finding in inspection.findings if finding.code in _NORMALIZATION_CODES]
    if not relevant:
        return None
    bounds = inspection.geometry.bounds
    matrix = np.eye(4, dtype=np.float64)
    components: list[NormalizationComponent] = []
    codes = {finding.code for finding in relevant}

    if "HEIGHT_OUT_OF_RANGE" in codes:
        dominant_index = {"X": 0, "Y": 1, "Z": 2}[inspection.geometry.dominant_dimension_axis]
        dominant_extent = bounds.dimensions_m[dominant_index]
        if dominant_extent <= 0:
            return None
        scale_factor = (profile.expected_height_cm.target / 100.0) / dominant_extent
        matrix = np.diag([scale_factor, scale_factor, scale_factor, 1.0]) @ matrix
        components.append(
            NormalizationComponent(
                component="scale",
                evidence=(
                    f"Dominant extent {dominant_extent:.9g} m versus target "
                    f"{profile.expected_height_cm.target / 100.0:.9g} m."
                ),
                confidence=0.99,
            )
        )
    if "ORIENTATION_NOT_Y_UP" in codes:
        rotation = _axis_to_positive_y(bounds, inspection.geometry.dominant_dimension_axis)
        matrix = rotation @ matrix
        components.append(
            NormalizationComponent(
                component="orientation",
                evidence=(
                    f"Dominant extent is on {inspection.geometry.dominant_dimension_axis}; "
                    "map its inferred positive direction to +Y."
                ),
                confidence=0.98,
            )
        )

    corners = _bounds_corners(bounds)
    homogeneous = np.column_stack((corners, np.ones(len(corners), dtype=np.float64)))
    transformed = (matrix @ homogeneous.T).T[:, :3]
    if "NOT_GROUNDED" in codes:
        translation = np.eye(4, dtype=np.float64)
        minimum_y_before_grounding = float(transformed[:, 1].min())
        translation[1, 3] = -minimum_y_before_grounding
        matrix = translation @ matrix
        transformed = (matrix @ homogeneous.T).T[:, :3]
        components.append(
            NormalizationComponent(
                component="grounding",
                evidence=(
                    f"Translate transformed minimum Y to 0 from {minimum_y_before_grounding:.9g} m."
                ),
                confidence=1.0,
            )
        )

    component_names = ", ".join(component.component for component in components)
    return CandidateRepair(
        id="normalize-root-v1",
        kind=RepairKind.NORMALIZATION_TRANSFORM,
        action_class=ActionClass.APPROVAL_REQUIRED,
        finding_ids=tuple(sorted(finding.id for finding in relevant)),
        description="Apply one reversible root normalization transform.",
        payload=NormalizationPayload(
            before_bounds=bounds,
            proposed_matrix=_matrix_model(matrix),
            expected_after_bounds=_bounds_from_points(transformed),
            components=tuple(components),
            consequence_summary=(
                f"This changes world-space {component_names} without modifying vertex data. "
                "The original file remains untouched."
            ),
        ),
    )


def plan_repairs(inspection: InspectionResult, profile: ProjectProfile) -> RepairPlan:
    """Generate only registered version-1 candidates from deterministic findings."""
    blocked_reasons: list[str] = []
    if inspection.repair_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH:
        blocked_reasons.append(f"Repair eligibility is {inspection.repair_eligibility}")
    candidates: list[CandidateRepair] = []
    if not blocked_reasons:
        naming = inspection.naming
        if naming is not None and profile.repair_policy.auto_rename:
            for component, replacement in sorted(naming.proposed_replacements.items()):
                component_type_text, index_text = component.split(":", maxsplit=1)
                component_type: Literal["node", "mesh"]
                if component_type_text == "node":
                    component_type = "node"
                elif component_type_text == "mesh":
                    component_type = "mesh"
                else:
                    continue
                component_index = int(index_text)
                candidate_id = f"rename-{component_type}-{component_index:03d}"
                finding_ids = tuple(
                    sorted(
                        finding.id
                        for finding in inspection.findings
                        if candidate_id in finding.candidate_repairs
                    )
                )
                if component_type == "node":
                    before_name = naming.node_names[component_index]
                    kind = RepairKind.RENAME_NODE
                else:
                    before_name = naming.mesh_names[component_index]
                    kind = RepairKind.RENAME_MESH
                candidates.append(
                    CandidateRepair(
                        id=candidate_id,
                        kind=kind,
                        action_class=ActionClass.AUTO_SAFE,
                        finding_ids=finding_ids,
                        description=(
                            f"Rename {component} to {replacement} while preserving its index."
                        ),
                        payload=RenamePayload(
                            component_type=component_type,
                            component_index=component_index,
                            before_name=before_name,
                            after_name=replacement,
                        ),
                    )
                )
        normalization = _normalization_candidate(inspection, profile)
        if normalization is not None:
            candidates.append(normalization)

    auto_ids = tuple(
        candidate.id for candidate in candidates if candidate.action_class is ActionClass.AUTO_SAFE
    )
    approval_ids = tuple(
        candidate.id
        for candidate in candidates
        if candidate.action_class is ActionClass.APPROVAL_REQUIRED
    )
    return RepairPlan(
        plan_id=f"plan-{inspection.package.file_sha256[:16]}-v1",
        inspection_id=inspection.inspection_id,
        source_sha256=inspection.package.file_sha256,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        candidates=tuple(candidates),
        auto_action_ids=auto_ids,
        approval_action_ids=approval_ids,
        blocked=bool(blocked_reasons),
        blocked_reasons=tuple(blocked_reasons),
    )
