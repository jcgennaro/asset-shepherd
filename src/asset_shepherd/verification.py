"""Independent deterministic verification of repaired GLB candidates."""

# Trimesh does not publish complete PEP 561 metadata.
# pyright: reportUnknownMemberType=false

from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import trimesh
from pydantic import JsonValue

from asset_shepherd.glb import GlbError, load_glb, validate_loaded_glb
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    CheckStatus,
    Decisions,
    DecisionValue,
    InspectionResult,
    NormalizationPayload,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationCheck,
    VerificationResult,
    VerificationState,
)
from asset_shepherd.planner import plan_repairs
from asset_shepherd.repair import RepairOutcome


def _check(
    code: str,
    passed: bool,
    description: str,
    *,
    expected: JsonValue = None,
    actual: JsonValue = None,
) -> VerificationCheck:
    return VerificationCheck(
        code=code,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        description=description,
        expected=expected,
        actual=actual,
    )


def verify_repair(
    source: Path,
    candidate: Path,
    profile: ProjectProfile,
    original: InspectionResult,
    plan: RepairPlan,
    decisions: Decisions,
    outcome: RepairOutcome,
    provenance: Provenance,
) -> VerificationResult:
    """Reload, independently inspect, and verify a repaired candidate from disk."""
    checks: list[VerificationCheck] = []
    source_hash = sha256(source.read_bytes()).hexdigest()
    candidate_bytes = candidate.read_bytes() if candidate.exists() else b""
    output_hash = sha256(candidate_bytes).hexdigest() if candidate_bytes else None
    checks.append(
        _check(
            "SOURCE_UNCHANGED",
            source_hash == plan.source_sha256 == outcome.source_sha256,
            "The original source hash is unchanged and matches the plan.",
            expected=plan.source_sha256,
            actual=source_hash,
        )
    )
    checks.append(
        _check(
            "OUTPUT_HASH_RECORDED",
            output_hash == outcome.output_sha256 == provenance.output_sha256,
            "The candidate hash matches repair outcome and provenance.",
            expected=outcome.output_sha256,
            actual=output_hash,
        )
    )

    validation_error: str | None = None
    try:
        loaded = load_glb(candidate)
        validate_loaded_glb(loaded)
    except (GlbError, OSError, ValueError, IndexError, TypeError) as error:
        validation_error = str(error)
    checks.append(
        _check(
            "GLTF_VALIDATION",
            validation_error is None,
            "The saved output parses as GLB 2.0 and passes selected structural validation.",
            expected="valid GLB 2.0",
            actual=validation_error or "valid GLB 2.0",
        )
    )

    output = inspect_asset(candidate, profile)
    checks.append(
        _check(
            "INDEPENDENT_REINSPECTION",
            output.package.parse_success,
            "A fresh disk reload produced a complete deterministic inspection.",
            expected=True,
            actual=output.package.parse_success,
        )
    )
    if original.geometry is not None and output.geometry is not None:
        count_pairs = (
            (
                "VERTEX_COUNT_PRESERVED",
                original.geometry.vertex_count,
                output.geometry.vertex_count,
            ),
            (
                "TRIANGLE_COUNT_PRESERVED",
                original.geometry.triangle_count,
                output.geometry.triangle_count,
            ),
            (
                "MATERIAL_COUNT_PRESERVED",
                original.package.material_count,
                output.package.material_count,
            ),
            (
                "TEXTURE_COUNT_PRESERVED",
                original.package.texture_count,
                output.package.texture_count,
            ),
        )
        for code, expected, actual in count_pairs:
            checks.append(
                _check(
                    code,
                    expected == actual,
                    code.replace("_", " ").title(),
                    expected=expected,
                    actual=actual,
                )
            )
        naming_valid = output.naming is not None and not output.naming.proposed_replacements
        checks.append(
            _check(
                "NAMES_VALID_AND_UNIQUE",
                naming_valid,
                "All node and mesh names satisfy the profile and uniqueness rules.",
                expected=True,
                actual=naming_valid,
            )
        )

        deterministic_bounds = np.asarray(
            [output.geometry.bounds.minimum_m, output.geometry.bounds.maximum_m],
            dtype=np.float64,
        )
        try:
            independent = trimesh.load_scene(candidate, process=False)
            independent_bounds = independent.bounds
            independent_matches = independent_bounds is not None and np.allclose(
                independent_bounds,
                deterministic_bounds,
                rtol=1e-6,
                atol=1e-7,
            )
            independent_actual: JsonValue = (
                cast(JsonValue, independent_bounds.tolist())
                if independent_bounds is not None
                else None
            )
        except (OSError, ValueError, IndexError, TypeError) as error:
            independent_matches = False
            independent_actual = str(error)
        checks.append(
            _check(
                "INDEPENDENT_GEOMETRY_RELOAD",
                independent_matches,
                "Trimesh independently reloads the GLB and agrees on world bounds.",
                expected=cast(JsonValue, deterministic_bounds.tolist()),
                actual=independent_actual,
            )
        )

    records = {record.candidate_id: record for record in decisions.records}
    normalization = next(
        (
            candidate
            for candidate in plan.candidates
            if isinstance(candidate.payload, NormalizationPayload)
        ),
        None,
    )
    if normalization is not None and output.geometry is not None and original.geometry is not None:
        record = records[normalization.id]
        normalization_payload = normalization.payload
        if not isinstance(normalization_payload, NormalizationPayload):
            raise TypeError("Normalization candidate has the wrong payload")
        component_names = {component.component for component in normalization_payload.components}
        if record.decision is DecisionValue.APPROVED:
            if "scale" in component_names:
                height_cm = output.geometry.bounds.dimensions_cm[1]
                target = profile.expected_height_cm.target
                tolerance = profile.expected_height_cm.tolerance
                checks.append(
                    _check(
                        "APPROVED_SCALE_WITHIN_TOLERANCE",
                        abs(height_cm - target) <= tolerance,
                        "Approved physical scale is within the project height tolerance.",
                        expected=cast(JsonValue, {"target_cm": target, "tolerance_cm": tolerance}),
                        actual=height_cm,
                    )
                )
            if "orientation" in component_names:
                checks.append(
                    _check(
                        "APPROVED_ORIENTATION_Y_UP",
                        output.geometry.dominant_dimension_axis == "Y",
                        "Approved upright normalization places the dominant extent on Y.",
                        expected="Y",
                        actual=output.geometry.dominant_dimension_axis,
                    )
                )
            if "grounding" in component_names:
                minimum_y_cm = output.geometry.bounds.minimum_cm[1]
                tolerance = profile.orientation.ground_tolerance_cm
                checks.append(
                    _check(
                        "APPROVED_GROUNDING_WITHIN_TOLERANCE",
                        abs(minimum_y_cm) <= tolerance,
                        "Approved grounding places the minimum point at Y=0 within tolerance.",
                        expected=cast(JsonValue, {"ground_cm": 0.0, "tolerance_cm": tolerance}),
                        actual=minimum_y_cm,
                    )
                )
        else:
            unchanged_bounds = np.allclose(
                [output.geometry.bounds.minimum_m, output.geometry.bounds.maximum_m],
                [original.geometry.bounds.minimum_m, original.geometry.bounds.maximum_m],
                rtol=1e-7,
                atol=1e-8,
            )
            checks.append(
                _check(
                    "REJECTED_NORMALIZATION_NOT_APPLIED",
                    unchanged_bounds and normalization.id in outcome.rejected_action_ids,
                    "Rejected normalization left world-space bounds unchanged.",
                    expected=cast(
                        JsonValue,
                        [
                            list(original.geometry.bounds.minimum_m),
                            list(original.geometry.bounds.maximum_m),
                        ],
                    ),
                    actual=cast(
                        JsonValue,
                        [
                            list(output.geometry.bounds.minimum_m),
                            list(output.geometry.bounds.maximum_m),
                        ],
                    ),
                )
            )

    provenance_ids = {action.candidate_id for action in provenance.executed_actions}
    checks.append(
        _check(
            "EXECUTED_ACTIONS_IN_PROVENANCE",
            provenance_ids == set(outcome.executed_action_ids),
            "Every executed repair action appears exactly in provenance.",
            expected=cast(JsonValue, sorted(outcome.executed_action_ids)),
            actual=cast(JsonValue, sorted(provenance_ids)),
        )
    )
    rejected_ids = frozenset(
        record.candidate_id
        for record in decisions.records
        if record.decision is DecisionValue.REJECTED
    )
    rejected_preserved = rejected_ids == frozenset(outcome.rejected_action_ids)
    checks.append(
        _check(
            "REJECTIONS_PRESERVED",
            rejected_preserved,
            "Rejected actions were not executed and remain rejected for this job.",
            expected=cast(JsonValue, sorted(rejected_ids)),
            actual=cast(JsonValue, sorted(outcome.rejected_action_ids)),
        )
    )
    second_plan = plan_repairs(
        output,
        profile,
        excluded_candidate_ids=rejected_ids,
    )
    checks.append(
        _check(
            "SECOND_PLAN_EMPTY",
            not second_plan.candidates,
            "A second version-1 planning pass proposes no non-rejected repairs.",
            expected=0,
            actual=len(second_plan.candidates),
        )
    )

    failed = any(check.status in {CheckStatus.FAIL, CheckStatus.BLOCKED} for check in checks)
    remaining_warnings = tuple(f"{finding.code}: {finding.title}" for finding in output.findings)
    if failed:
        state = VerificationState.FAILED
    elif remaining_warnings:
        state = VerificationState.PASSED_WITH_REMAINING_WARNINGS
    else:
        state = VerificationState.PASSED_PROJECT_READY
    return VerificationResult(
        verification_id=f"verification-{(output_hash or source_hash)[:16]}-v1",
        source_sha256=source_hash,
        output_sha256=output_hash,
        state=state,
        checks=tuple(checks),
        remaining_warnings=remaining_warnings,
        second_plan_candidate_count=len(second_plan.candidates),
    )
