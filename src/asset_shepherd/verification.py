"""Independent deterministic verification of repaired GLB candidates."""

# Trimesh does not publish complete PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import trimesh
from pydantic import JsonValue
from pygltflib import GLTF2

from asset_shepherd.glb import GlbError, load_glb, node_local_matrix, validate_loaded_glb
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.khronos import (
    KhronosValidatorError,
    KhronosValidatorUnavailable,
    find_khronos_validator,
    validate_with_khronos,
)
from asset_shepherd.models import (
    CheckBasis,
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
    basis: CheckBasis = CheckBasis.UNIVERSAL_INVARIANT,
    expected: JsonValue = None,
    actual: JsonValue = None,
) -> VerificationCheck:
    return VerificationCheck(
        code=code,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        description=description,
        basis=basis,
        expected=expected,
        actual=actual,
    )


def _status_check(
    code: str,
    status: CheckStatus,
    description: str,
    *,
    basis: CheckBasis,
    expected: JsonValue = None,
    actual: JsonValue = None,
) -> VerificationCheck:
    return VerificationCheck(
        code=code,
        status=status,
        description=description,
        basis=basis,
        expected=expected,
        actual=actual,
    )


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        allow_nan=True,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _without_display_names(records: object) -> object:
    if not isinstance(records, list):
        return records
    normalized: list[object] = []
    for record in cast(list[object], records):
        if isinstance(record, dict):
            mapping = cast(dict[str, object], record)
            normalized.append({key: value for key, value in mapping.items() if key != "name"})
        else:
            normalized.append(record)
    return normalized


def _document_section(document: dict[str, object], name: str) -> object:
    return document.get(name, [])


def _preservation_checks(
    source_gltf: GLTF2,
    output_gltf: GLTF2,
    plan: RepairPlan,
    outcome: RepairOutcome,
) -> list[VerificationCheck]:
    # ``GLTF2.to_dict`` leaves nested helper objects such as ``Attributes``
    # intact.  Round-tripping its JSON representation produces the same
    # semantic document using only JSON-compatible values.
    source_document = cast(dict[str, object], json.loads(source_gltf.to_json()))
    output_document = cast(dict[str, object], json.loads(output_gltf.to_json()))
    checks: list[VerificationCheck] = []

    section_checks = (
        ("ACCESSOR_DEFINITIONS_PRESERVED", "accessors"),
        ("BUFFER_VIEW_DEFINITIONS_PRESERVED", "bufferViews"),
        ("BUFFER_DEFINITIONS_PRESERVED", "buffers"),
        ("MATERIAL_DEFINITIONS_PRESERVED", "materials"),
        ("TEXTURE_DEFINITIONS_PRESERVED", "textures"),
        ("IMAGE_DEFINITIONS_PRESERVED", "images"),
        ("SAMPLER_DEFINITIONS_PRESERVED", "samplers"),
        ("ANIMATION_DEFINITIONS_PRESERVED", "animations"),
        ("SKIN_DEFINITIONS_PRESERVED", "skins"),
        ("CAMERA_DEFINITIONS_PRESERVED", "cameras"),
    )
    for code, section in section_checks:
        source_hash = _canonical_hash(_document_section(source_document, section))
        output_hash = _canonical_hash(_document_section(output_document, section))
        checks.append(
            _check(
                code,
                source_hash == output_hash,
                f"The {section} records are semantically unchanged.",
                expected=source_hash,
                actual=output_hash,
            )
        )

    source_mesh_hash = _canonical_hash(
        _without_display_names(_document_section(source_document, "meshes"))
    )
    output_mesh_hash = _canonical_hash(
        _without_display_names(_document_section(output_document, "meshes"))
    )
    checks.append(
        _check(
            "MESH_PRIMITIVES_PRESERVED",
            source_mesh_hash == output_mesh_hash,
            "Mesh primitives, attributes, topology, material references, and extras are unchanged.",
            expected=source_mesh_hash,
            actual=output_mesh_hash,
        )
    )

    source_nodes = cast(list[object], _document_section(source_document, "nodes"))
    output_nodes = cast(list[object], _document_section(output_document, "nodes"))
    source_node_hash = _canonical_hash(_without_display_names(source_nodes))
    output_original_node_hash = _canonical_hash(
        _without_display_names(output_nodes[: len(source_nodes)])
    )
    checks.append(
        _check(
            "ORIGINAL_NODE_REFERENCES_PRESERVED",
            source_node_hash == output_original_node_hash,
            "Every original node keeps its non-name references and transform payload.",
            expected=source_node_hash,
            actual=output_original_node_hash,
        )
    )

    source_blob = cast(bytes | bytearray | None, source_gltf.binary_blob())
    output_blob = cast(bytes | bytearray | None, output_gltf.binary_blob())
    source_blob_hash = sha256(bytes(source_blob or b"")).hexdigest()
    output_blob_hash = sha256(bytes(output_blob or b"")).hexdigest()
    checks.append(
        _check(
            "BINARY_PAYLOAD_PRESERVED",
            source_blob_hash == output_blob_hash,
            "The complete embedded binary payload, including geometry and images, is unchanged.",
            expected=source_blob_hash,
            actual=output_blob_hash,
        )
    )

    top_level = {
        key: source_document.get(key)
        for key in ("extensions", "extensionsRequired", "extensionsUsed", "extras")
    }
    output_top_level = {
        key: output_document.get(key)
        for key in ("extensions", "extensionsRequired", "extensionsUsed", "extras")
    }
    checks.append(
        _check(
            "TOP_LEVEL_EXTENSION_METADATA_PRESERVED",
            top_level == output_top_level,
            "Top-level extension declarations, extension payloads, and extras are unchanged.",
            expected=cast(JsonValue, top_level),
            actual=cast(JsonValue, output_top_level),
        )
    )

    normalization = next(
        (
            candidate
            for candidate in plan.candidates
            if isinstance(candidate.payload, NormalizationPayload)
            and candidate.id in outcome.executed_action_ids
        ),
        None,
    )
    expected_node_count = len(source_nodes) + (1 if normalization is not None else 0)
    checks.append(
        _check(
            "AUTHORIZED_NODE_COUNT_CHANGE_ONLY",
            len(output_nodes) == expected_node_count,
            "Only an approved reversible normalization root may change the node count.",
            expected=expected_node_count,
            actual=len(output_nodes),
        )
    )

    configured_source_scene = cast(int | None, source_gltf.scene)
    configured_output_scene = cast(int | None, output_gltf.scene)
    source_scene_index = configured_source_scene if configured_source_scene is not None else 0
    output_scene_index = configured_output_scene if configured_output_scene is not None else 0
    source_roots = tuple(source_gltf.scenes[source_scene_index].nodes or ())
    output_roots = tuple(output_gltf.scenes[output_scene_index].nodes or ())
    if normalization is None:
        root_change_valid = source_roots == output_roots
        root_actual: JsonValue = list(output_roots)
        root_expected: JsonValue = list(source_roots)
    else:
        payload = normalization.payload
        if not isinstance(payload, NormalizationPayload) or not output_nodes:
            root_change_valid = False
        else:
            root_index = len(output_nodes) - 1
            root_node = output_gltf.nodes[root_index]
            root_change_valid = (
                output_roots == (root_index,)
                and tuple(root_node.children or ()) == source_roots
                and np.allclose(
                    node_local_matrix(root_node),
                    np.asarray(payload.proposed_matrix, dtype=np.float64),
                    rtol=0.0,
                    atol=1e-12,
                )
            )
        root_expected = cast(
            JsonValue,
            {
                "scene_roots": [len(output_nodes) - 1],
                "normalization_children": list(source_roots),
            },
        )
        root_actual = cast(
            JsonValue,
            {
                "scene_roots": list(output_roots),
                "normalization_children": (
                    list(output_gltf.nodes[-1].children or ()) if output_nodes else []
                ),
            },
        )
    checks.append(
        _check(
            "SCENE_ROOT_CHANGE_AUTHORIZED",
            root_change_valid,
            "The scene-root change exactly matches the approved normalization plan.",
            expected=root_expected,
            actual=root_actual,
        )
    )
    return checks


def _khronos_checks(
    source: Path, candidate: Path
) -> tuple[list[VerificationCheck], tuple[str, ...]]:
    validator = find_khronos_validator()
    if validator is None:
        return [], ()
    try:
        source_result = validate_with_khronos(source, executable=validator)
        output_result = validate_with_khronos(candidate, executable=validator)
    except (KhronosValidatorError, KhronosValidatorUnavailable, OSError) as error:
        return (
            [
                _check(
                    "KHRONOS_VALIDATOR_EXECUTED",
                    False,
                    "The configured official Khronos validator must produce source and output "
                    "reports.",
                    basis=CheckBasis.EXTERNAL_CONSUMER_EVIDENCE,
                    expected="two readable official reports",
                    actual=str(error),
                )
            ],
            (),
        )

    checks = [
        _check(
            "KHRONOS_VALIDATOR_EXECUTED",
            True,
            "The official Khronos validator independently checked source and output bytes.",
            basis=CheckBasis.EXTERNAL_CONSUMER_EVIDENCE,
            expected=source_result.validator_version,
            actual=output_result.validator_version,
        )
    ]
    new_error_fingerprints = Counter(output_result.error_fingerprints) - Counter(
        source_result.error_fingerprints
    )
    no_new_errors = (
        output_result.error_count <= source_result.error_count and not new_error_fingerprints
    )
    checks.append(
        _check(
            "KHRONOS_ERRORS_NOT_INTRODUCED",
            no_new_errors,
            "Repair must not introduce any new official glTF validation error.",
            expected=cast(
                JsonValue,
                {
                    "maximum_error_count": source_result.error_count,
                    "allowed_error_fingerprints": list(source_result.error_fingerprints),
                },
            ),
            actual=cast(
                JsonValue,
                {
                    "error_count": output_result.error_count,
                    "error_codes": list(output_result.error_codes),
                    "new_error_fingerprints": sorted(new_error_fingerprints.elements()),
                },
            ),
        )
    )
    conformance_status = CheckStatus.PASS if output_result.error_count == 0 else CheckStatus.WARNING
    checks.append(
        _status_check(
            "KHRONOS_OUTPUT_CONFORMANCE",
            conformance_status,
            (
                "The output has no official glTF validation errors."
                if output_result.error_count == 0
                else (
                    "The output preserves official validation errors already present in the source."
                )
            ),
            basis=CheckBasis.OBJECTIVE_SOURCE_DIAGNOSTIC,
            expected=0,
            actual=cast(
                JsonValue,
                {
                    "errors": output_result.error_count,
                    "warnings": output_result.warning_count,
                    "infos": output_result.info_count,
                    "hints": output_result.hint_count,
                    "issue_codes": list(output_result.issue_codes),
                },
            ),
        )
    )
    warnings: list[str] = []
    if output_result.error_count:
        warnings.append(
            "KHRONOS_VALIDATION_ERRORS: "
            f"{output_result.error_count} source-retained error(s): "
            f"{', '.join(output_result.error_codes)}"
        )
    if output_result.warning_count:
        warnings.append(
            "KHRONOS_VALIDATION_WARNINGS: "
            f"{output_result.warning_count} warning(s): "
            f"{', '.join(output_result.warning_codes)}"
        )
    return checks, tuple(warnings)


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
    source_loaded: GLTF2 | None = None
    loaded: GLTF2 | None = None
    try:
        source_loaded = load_glb(source)
        validate_loaded_glb(source_loaded)
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

    if source_loaded is not None and loaded is not None:
        checks.extend(_preservation_checks(source_loaded, loaded, plan, outcome))
    khronos_checks, khronos_warnings = _khronos_checks(source, candidate)
    checks.extend(khronos_checks)

    output = inspect_asset(candidate, profile, policy=provenance.profile_policy)
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
                basis=CheckBasis.FROZEN_PROJECT_POLICY,
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
                        basis=CheckBasis.FROZEN_PROJECT_POLICY,
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
                        basis=CheckBasis.FROZEN_PROJECT_POLICY,
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
                        basis=CheckBasis.FROZEN_PROJECT_POLICY,
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
            basis=CheckBasis.FROZEN_PROJECT_POLICY,
            expected=0,
            actual=len(second_plan.candidates),
        )
    )

    failed = any(check.status in {CheckStatus.FAIL, CheckStatus.BLOCKED} for check in checks)
    remaining_warnings = (
        *(f"{finding.code}: {finding.title}" for finding in output.findings),
        *khronos_warnings,
    )
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
