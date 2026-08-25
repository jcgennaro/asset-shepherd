"""Deterministic version-1 candidate repair planning."""

from itertools import product
from math import cos, radians, sin
from typing import Literal

import numpy as np

from asset_shepherd.models import (
    ActionClass,
    AgentDisposition,
    AgentRepairAssessment,
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
    WeldPayload,
    WeldPrimitivePayload,
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


def _axis_rotation(axis: Literal["X", "Y", "Z"], degrees: int) -> np.ndarray:
    """Return one bounded right-handed world rotation requested by the workflow agent."""
    angle = radians(degrees)
    cosine = float(round(cos(angle), 15))
    sine = float(round(sin(angle), 15))
    rotation = np.eye(4, dtype=np.float64)
    if axis == "X":
        rotation[:3, :3] = np.asarray([[1.0, 0.0, 0.0], [0.0, cosine, -sine], [0.0, sine, cosine]])
    elif axis == "Y":
        rotation[:3, :3] = np.asarray([[cosine, 0.0, sine], [0.0, 1.0, 0.0], [-sine, 0.0, cosine]])
    else:
        rotation[:3, :3] = np.asarray([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])
    return rotation


def _rename_candidates(
    inspection: InspectionResult,
    profile: ProjectProfile,
) -> list[CandidateRepair]:
    """Build only index-preserving display-name actions from measured naming facts."""
    candidates: list[CandidateRepair] = []
    naming = inspection.naming
    if naming is None or not profile.repair_policy.auto_rename:
        return candidates
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
                description=f"Rename {component} to {replacement} while preserving its index.",
                payload=RenamePayload(
                    component_type=component_type,
                    component_index=component_index,
                    before_name=before_name,
                    after_name=replacement,
                ),
            )
        )
    return candidates


def _attribute_safe_weld_candidate(
    inspection: InspectionResult,
) -> CandidateRepair | None:
    """Register only complete vertex-tuple compaction proven by inspection evidence."""
    if inspection.diagnostics is None:
        return None
    mergeable = tuple(
        primitive
        for primitive in inspection.diagnostics.primitives
        if primitive.attribute_safe_merge_count > 0
    )
    if not mergeable:
        return None
    protected_attributes = tuple(
        sorted(
            {
                semantic
                for primitive in inspection.diagnostics.primitives
                for semantic in primitive.attribute_semantics
            }
        )
    )
    duplicate_finding_ids = tuple(
        finding.id
        for finding in inspection.findings
        if finding.code == "ATTRIBUTE_SAFE_DUPLICATE_TUPLES_DETECTED"
    )
    return CandidateRepair(
        id="weld-identical-vertices-v1",
        kind=RepairKind.WELD_IDENTICAL_VERTICES,
        action_class=ActionClass.AUTO_SAFE,
        finding_ids=duplicate_finding_ids,
        description=(
            "Compact byte-identical complete vertex tuples while retaining every protected "
            "attribute seam."
        ),
        payload=WeldPayload(
            primitives=tuple(
                WeldPrimitivePayload(
                    mesh_index=primitive.mesh_index,
                    primitive_index=primitive.primitive_index,
                    before_position_count=primitive.position_count,
                    after_position_count=(
                        primitive.position_count - primitive.attribute_safe_merge_count
                    ),
                    merge_count=primitive.attribute_safe_merge_count,
                )
                for primitive in mergeable
            ),
            protected_attributes=protected_attributes,
            consequence_summary=(
                "This changes index and vertex-buffer layout only where complete vertex tuples "
                "are byte-identical; UV, normal, color, and skinning seams remain split."
            ),
        ),
    )


def plan_agent_repairs(
    inspection: InspectionResult,
    profile: ProjectProfile,
    assessment: AgentRepairAssessment,
    *,
    confirmed_target_height_m: float,
    confirmed_target_dimensions_m: tuple[float, float, float] | None = None,
) -> RepairPlan:
    """Preview exactly the bounded actions requested by a model-authored assessment."""
    blocked_reasons: list[str] = []
    if inspection.repair_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH:
        blocked_reasons.append(f"Repair eligibility is {inspection.repair_eligibility}")
    if assessment.disposition is AgentDisposition.NEEDS_CLARIFICATION:
        blocked_reasons.append("The workflow agent needs a material target clarification")
    if assessment.disposition is AgentDisposition.RETURN_TO_CREATION_TOOL:
        blocked_reasons.append("The workflow agent found no supported repair path")
    candidates: list[CandidateRepair] = []
    if not blocked_reasons and assessment.disposition is AgentDisposition.REPAIR:
        if assessment.rename_invalid_display_names:
            candidates.extend(_rename_candidates(inspection, profile))
        if assessment.weld_identical_vertices:
            weld_candidate = _attribute_safe_weld_candidate(inspection)
            if weld_candidate is None:
                raise ValueError(
                    "The agent requested welding, but inspection found no attribute-safe "
                    "duplicate vertex tuples"
                )
            candidates.append(weld_candidate)

        transform_requested = any(
            (
                assessment.scale_to_confirmed_height,
                assessment.rotation_degrees != 0,
                assessment.ground_to_y_zero,
            )
        )
        if transform_requested:
            if inspection.geometry is None:
                raise ValueError("A physical action requires measured geometry bounds")
            bounds = inspection.geometry.bounds
            matrix = np.eye(4, dtype=np.float64)
            components: list[NormalizationComponent] = []

            if assessment.scale_to_confirmed_height:
                if confirmed_target_dimensions_m is not None:
                    target_dimensions = np.asarray(
                        confirmed_target_dimensions_m,
                        dtype=np.float64,
                    )
                    if not np.isfinite(target_dimensions).all() or np.any(target_dimensions <= 0):
                        raise ValueError("Confirmed target dimensions must be finite and positive")
                    fitting_matrix = (
                        _axis_rotation(assessment.rotation_axis, assessment.rotation_degrees)
                        if assessment.rotation_degrees != 0 and assessment.rotation_axis is not None
                        else np.eye(4, dtype=np.float64)
                    )
                    fitting_corners = _bounds_corners(bounds)
                    fitting_homogeneous = np.column_stack(
                        (fitting_corners, np.ones(len(fitting_corners), dtype=np.float64))
                    )
                    fitting_points = (fitting_matrix @ fitting_homogeneous.T).T[:, :3]
                    source_dimensions = np.ptp(fitting_points, axis=0)
                    if np.any(source_dimensions <= 0):
                        raise ValueError("Every fitted source dimension must be positive")
                    axis_factors = target_dimensions / source_dimensions
                    scale_factor = float(np.median(axis_factors))
                    fitted_dimensions = source_dimensions * scale_factor
                    evidence = (
                        "The confirmed X/Y/Z dimensions are approximate. The deterministic "
                        f"uniform median fit chose {scale_factor:.9g} from axis factors "
                        f"{axis_factors[0]:.6g}, {axis_factors[1]:.6g}, "
                        f"{axis_factors[2]:.6g}; expected extents are "
                        f"{fitted_dimensions[0]:.6g} x {fitted_dimensions[1]:.6g} x "
                        f"{fitted_dimensions[2]:.6g} m. Proportions remain unchanged."
                    )
                else:
                    axis = assessment.semantic_height_axis
                    if axis is None:
                        raise ValueError("Scaling requires an agent-selected semantic height axis")
                    extent = bounds.dimensions_m[{"X": 0, "Y": 1, "Z": 2}[axis]]
                    if extent <= 0:
                        raise ValueError("The selected semantic height extent is not positive")
                    scale_factor = confirmed_target_height_m / extent
                    evidence = (
                        f"The agent identified source {axis} ({extent:.9g} m) as semantic "
                        f"height and requested the confirmed {confirmed_target_height_m:.9g} m "
                        "target."
                    )
                matrix = np.diag([scale_factor, scale_factor, scale_factor, 1.0]) @ matrix
                components.append(
                    NormalizationComponent(
                        component="scale",
                        evidence=evidence,
                        confidence=assessment.confidence,
                    )
                )

            if assessment.rotation_degrees != 0:
                axis = assessment.rotation_axis
                if axis is None:
                    raise ValueError("Rotation requires an agent-selected axis")
                matrix = _axis_rotation(axis, assessment.rotation_degrees) @ matrix
                components.append(
                    NormalizationComponent(
                        component="orientation",
                        evidence=(
                            f"The agent requested a {assessment.rotation_degrees:+d} degree "
                            f"rotation around {axis} after reviewing: "
                            f"{', '.join(assessment.source_views_used)}."
                        ),
                        confidence=assessment.confidence,
                    )
                )

            corners = _bounds_corners(bounds)
            homogeneous = np.column_stack((corners, np.ones(len(corners), dtype=np.float64)))
            transformed = (matrix @ homogeneous.T).T[:, :3]
            if assessment.ground_to_y_zero:
                minimum_y = float(transformed[:, 1].min())
                translation = np.eye(4, dtype=np.float64)
                translation[1, 3] = -minimum_y
                matrix = translation @ matrix
                transformed = (matrix @ homogeneous.T).T[:, :3]
                components.append(
                    NormalizationComponent(
                        component="grounding",
                        evidence=f"The agent requested minimum Y move from {minimum_y:.9g} m to 0.",
                        confidence=assessment.confidence,
                    )
                )

            component_names = ", ".join(component.component for component in components)
            candidates.append(
                CandidateRepair(
                    id="normalize-root-v1",
                    kind=RepairKind.NORMALIZATION_TRANSFORM,
                    action_class=ActionClass.APPROVAL_REQUIRED,
                    finding_ids=tuple(
                        f"{assessment.assessment_id}:{component.component}"
                        for component in components
                    ),
                    description="Apply the agent-requested reversible root transform.",
                    payload=NormalizationPayload(
                        before_bounds=bounds,
                        proposed_matrix=_matrix_model(matrix),
                        expected_after_bounds=_bounds_from_points(transformed),
                        components=tuple(components),
                        consequence_summary=(
                            f"This changes world-space {component_names} as assessed by the agent."
                        ),
                    ),
                )
            )

        if not candidates:
            raise ValueError("The agent requested repair but no supported action was applicable")

    auto_ids = tuple(
        candidate.id for candidate in candidates if candidate.action_class is ActionClass.AUTO_SAFE
    )
    approval_ids = tuple(
        candidate.id
        for candidate in candidates
        if candidate.action_class is ActionClass.APPROVAL_REQUIRED
    )
    return RepairPlan(
        plan_id=f"agent-plan-{inspection.package.file_sha256[:16]}-v1",
        inspection_id=inspection.inspection_id,
        source_sha256=inspection.package.file_sha256,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        candidates=tuple(candidates),
        auto_action_ids=auto_ids,
        approval_action_ids=approval_ids,
        blocked=bool(blocked_reasons),
        blocked_reasons=tuple(blocked_reasons),
        planning_authority="AGENT_ORCHESTRATED",
        agent_assessment_id=assessment.assessment_id,
    )


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
    minimum_y_before_grounding = float(transformed[:, 1].min())
    ground_tolerance_m = profile.orientation.ground_tolerance_cm / 100.0
    transformed_breaks_ground_rule = not (0.0 <= minimum_y_before_grounding <= ground_tolerance_m)
    grounding_required = "NOT_GROUNDED" in codes or (
        profile.orientation.require_ground_contact and transformed_breaks_ground_rule
    )
    if grounding_required:
        translation = np.eye(4, dtype=np.float64)
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
                f"This changes world-space {component_names} without modifying vertex data."
            ),
        ),
    )


def plan_repairs(
    inspection: InspectionResult,
    profile: ProjectProfile,
    *,
    excluded_candidate_ids: frozenset[str] = frozenset(),
) -> RepairPlan:
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
    candidates = [
        candidate for candidate in candidates if candidate.id not in excluded_candidate_ids
    ]

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
