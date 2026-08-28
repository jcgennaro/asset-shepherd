"""Independent deterministic verification of repaired GLB candidates."""

# Trimesh does not publish complete PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
import trimesh
from pydantic import JsonValue
from pygltflib import GLTF2

from asset_shepherd.glb import (
    GlbError,
    accessor_array,
    degenerate_triangle_mask,
    load_glb,
    node_local_matrix,
    validate_loaded_glb,
)
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.khronos import (
    KhronosValidatorError,
    KhronosValidatorUnavailable,
    find_khronos_validator,
    validate_with_khronos,
)
from asset_shepherd.mesh_diagnostics import enumerate_connected_components
from asset_shepherd.models import (
    CheckBasis,
    CheckStatus,
    ComponentRemovalPayload,
    Decisions,
    DecisionValue,
    DegenerateGeometryPayload,
    InspectionResult,
    NormalizationPayload,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationCheck,
    VerificationResult,
    VerificationState,
    WeldPayload,
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


def _trimesh_referenced_bounds(scene: trimesh.Scene) -> np.ndarray | None:
    """Measure only face-referenced vertices through Trimesh's independent scene loader."""
    minimum = np.full(3, np.inf, dtype=np.float64)
    maximum = np.full(3, -np.inf, dtype=np.float64)
    found = False
    for node_name in cast(list[str], scene.graph.nodes_geometry):
        raw_transform, geometry_name = cast(tuple[object, str], scene.graph[node_name])
        geometry = cast(trimesh.Trimesh, scene.geometry[geometry_name])
        vertices = np.asarray(cast(npt.ArrayLike, geometry.vertices), dtype=np.float64)
        faces = np.asarray(cast(npt.ArrayLike, geometry.faces), dtype=np.int64)
        if not len(vertices) or not faces.size:
            continue
        referenced = np.unique(faces.reshape(-1))
        if np.any(referenced < 0) or np.any(referenced >= len(vertices)):
            return None
        homogeneous = np.column_stack(
            (vertices[referenced], np.ones(len(referenced), dtype=np.float64))
        )
        transform = np.asarray(cast(npt.ArrayLike, raw_transform), dtype=np.float64)
        transformed = (transform @ homogeneous.T).T[:, :3]
        minimum = np.minimum(minimum, transformed.min(axis=0))
        maximum = np.maximum(maximum, transformed.max(axis=0))
        found = True
    return np.asarray([minimum, maximum]) if found else None


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


def _record_byte_length(record: dict[str, object]) -> int:
    value = record.get("byteLength", 0)
    return value if isinstance(value, int) else 0


def _executed_weld(plan: RepairPlan, outcome: RepairOutcome) -> WeldPayload | None:
    return next(
        (
            candidate.payload
            for candidate in plan.candidates
            if candidate.id in outcome.executed_action_ids
            and isinstance(candidate.payload, WeldPayload)
        ),
        None,
    )


def _executed_degenerate_cleanup(
    plan: RepairPlan, outcome: RepairOutcome
) -> DegenerateGeometryPayload | None:
    """Return the exact executed degenerate cleanup payload, if any."""
    return next(
        (
            candidate.payload
            for candidate in plan.candidates
            if candidate.id in outcome.executed_action_ids
            and isinstance(candidate.payload, DegenerateGeometryPayload)
        ),
        None,
    )


def _executed_component_removal(
    plan: RepairPlan, outcome: RepairOutcome
) -> ComponentRemovalPayload | None:
    """Return the exact executed disconnected-component selection, if any."""
    return next(
        (
            candidate.payload
            for candidate in plan.candidates
            if candidate.id in outcome.executed_action_ids
            and isinstance(candidate.payload, ComponentRemovalPayload)
        ),
        None,
    )


def _executed_normalization(
    plan: RepairPlan, outcome: RepairOutcome
) -> NormalizationPayload | None:
    """Return the exact executed normalization payload, if any."""
    return next(
        (
            candidate.payload
            for candidate in plan.candidates
            if candidate.id in outcome.executed_action_ids
            and isinstance(candidate.payload, NormalizationPayload)
        ),
        None,
    )


def _corner_attribute_hash(
    gltf: GLTF2,
    *,
    omit_degenerate_for: frozenset[tuple[int, int]] = frozenset(),
    omit_component_ids: dict[tuple[int, int], frozenset[str]] | None = None,
) -> str:
    """Hash rendered primitive inputs after expanding every vertex attribute by index."""
    records: list[object] = []
    for mesh_index, mesh in enumerate(gltf.meshes):
        for primitive_index, primitive in enumerate(mesh.primitives):
            attribute_indices = {
                semantic: accessor_index
                for semantic, accessor_index in vars(primitive.attributes).items()
                if isinstance(accessor_index, int)
            }
            position_index = attribute_indices.get("POSITION")
            if position_index is None:
                raise GlbError("Primitive has no POSITION accessor")
            position_count = len(accessor_array(gltf, position_index))
            if primitive.indices is None:
                indices: np.ndarray[tuple[int], np.dtype[np.int64]] = np.arange(
                    position_count, dtype=np.int64
                )
            else:
                indices = np.asarray(
                    accessor_array(gltf, primitive.indices),
                    dtype=np.int64,
                ).reshape(-1)
            if (mesh_index, primitive_index) in omit_degenerate_for:
                if len(indices) % 3:
                    raise GlbError("Cleanup verification found an incomplete triangle")
                triangles: np.ndarray[tuple[int, int], np.dtype[np.int64]] = indices.reshape(
                    (-1, 3)
                )
                positions = np.asarray(accessor_array(gltf, position_index), dtype=np.float64)
                indices = triangles[~degenerate_triangle_mask(positions, triangles)].reshape(-1)
            component_ids = (omit_component_ids or {}).get((mesh_index, primitive_index))
            if component_ids:
                if len(indices) % 3:
                    raise GlbError("Component-removal verification found an incomplete triangle")
                triangles = indices.reshape((-1, 3))
                positions = np.asarray(accessor_array(gltf, position_index), dtype=np.float64)
                inventory = enumerate_connected_components(
                    positions,
                    triangles,
                    mesh_index=mesh_index,
                    primitive_index=primitive_index,
                )
                by_id = {component.component_id: component for component in inventory.components}
                if not component_ids <= set(by_id):
                    raise GlbError("Approved source component IDs are no longer reproducible")
                removed_faces = {
                    face
                    for component_id in component_ids
                    for face in by_id[component_id].face_indices
                }
                keep_mask = np.ones(len(triangles), dtype=bool)
                keep_mask[list(removed_faces)] = False
                indices = triangles[keep_mask].reshape(-1)
            attributes = {
                semantic: sha256(
                    np.ascontiguousarray(accessor_array(gltf, accessor_index)[indices]).tobytes()
                ).hexdigest()
                for semantic, accessor_index in sorted(attribute_indices.items())
            }
            records.append(
                {
                    "mesh": mesh_index,
                    "primitive": primitive_index,
                    "mode": primitive.mode,
                    "material": primitive.material,
                    "attributes": attributes,
                    "targets": primitive.targets,
                    "extensions": primitive.extensions,
                    "extras": primitive.extras,
                }
            )
    return _canonical_hash(records)


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
    weld = _executed_weld(plan, outcome)
    cleanup = _executed_degenerate_cleanup(plan, outcome)
    component_removal = _executed_component_removal(plan, outcome)
    append_only_geometry = weld is not None or cleanup is not None or component_removal is not None
    normalization = _executed_normalization(plan, outcome)

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
        source_section = _document_section(source_document, section)
        output_section = _document_section(output_document, section)
        if append_only_geometry and section in {"accessors", "bufferViews"}:
            source_records = cast(list[object], source_section)
            output_records = cast(list[object], output_section)
            preserved = source_records == output_records[: len(source_records)]
            source_hash = _canonical_hash(source_records)
            output_hash = _canonical_hash(output_records[: len(source_records)])
        elif append_only_geometry and section == "buffers":
            source_records = cast(list[dict[str, object]], source_section)
            output_records = cast(list[dict[str, object]], output_section)
            preserved = len(source_records) == len(output_records) and all(
                {key: value for key, value in source_item.items() if key != "byteLength"}
                == {key: value for key, value in output_item.items() if key != "byteLength"}
                and _record_byte_length(output_item) >= _record_byte_length(source_item)
                for source_item, output_item in zip(source_records, output_records, strict=True)
            )
            source_hash = _canonical_hash(source_records)
            output_hash = _canonical_hash(output_records)
        else:
            source_hash = _canonical_hash(source_section)
            output_hash = _canonical_hash(output_section)
            preserved = source_hash == output_hash
        checks.append(
            _check(
                code,
                preserved,
                (
                    f"The original {section} records are preserved and authorized weld data is "
                    "append-only."
                    if append_only_geometry and section in {"accessors", "bufferViews", "buffers"}
                    else f"The {section} records are semantically unchanged."
                ),
                expected=source_hash,
                actual=output_hash,
            )
        )

    if not append_only_geometry:
        source_mesh_hash = _canonical_hash(
            _without_display_names(_document_section(source_document, "meshes"))
        )
        output_mesh_hash = _canonical_hash(
            _without_display_names(_document_section(output_document, "meshes"))
        )
    else:
        cleanup_targets: frozenset[tuple[int, int]] = (
            frozenset(
                (primitive.mesh_index, primitive.primitive_index)
                for primitive in cleanup.primitives
            )
            if cleanup is not None
            else frozenset[tuple[int, int]]()
        )
        removed_component_ids = (
            {
                (primitive.mesh_index, primitive.primitive_index): frozenset(
                    primitive.removed_component_ids
                )
                for primitive in component_removal.primitives
            }
            if component_removal is not None
            else {}
        )
        source_mesh_hash = _corner_attribute_hash(
            source_gltf,
            omit_degenerate_for=cleanup_targets,
            omit_component_ids=removed_component_ids,
        )
        output_mesh_hash = _corner_attribute_hash(output_gltf)
    checks.append(
        _check(
            "MESH_PRIMITIVES_PRESERVED",
            source_mesh_hash == output_mesh_hash,
            (
                "Every surviving expanded primitive corner retains identical attributes and draw "
                "metadata."
                if append_only_geometry
                else (
                    "Mesh primitives, attributes, topology, material references, and extras are "
                    "unchanged."
                )
            ),
            expected=source_mesh_hash,
            actual=output_mesh_hash,
        )
    )

    source_nodes = cast(list[object], _document_section(source_document, "nodes"))
    output_nodes = cast(list[object], _document_section(output_document, "nodes"))
    source_nodes_for_hash = cast(list[object], json.loads(json.dumps(source_nodes)))
    output_nodes_for_hash = cast(
        list[object], json.loads(json.dumps(output_nodes[: len(source_nodes)]))
    )
    composed_root_index = (
        normalization.existing_root_index
        if normalization is not None and normalization.application_mode == "COMPOSE_EXISTING_ROOT"
        else None
    )
    if composed_root_index is not None:
        for records in (source_nodes_for_hash, output_nodes_for_hash):
            record = records[composed_root_index]
            if isinstance(record, dict):
                cast(dict[str, object], record).pop("matrix", None)
    source_node_hash = _canonical_hash(_without_display_names(source_nodes_for_hash))
    output_original_node_hash = _canonical_hash(_without_display_names(output_nodes_for_hash))
    checks.append(
        _check(
            "ORIGINAL_NODE_REFERENCES_PRESERVED",
            source_node_hash == output_original_node_hash,
            (
                "Every original node keeps its non-name references; only the proven prior "
                "normalization root receives the approved composed matrix."
                if composed_root_index is not None
                else "Every original node keeps its non-name references and transform payload."
            ),
            expected=source_node_hash,
            actual=output_original_node_hash,
        )
    )

    source_blob = cast(bytes | bytearray | None, source_gltf.binary_blob())
    output_blob = cast(bytes | bytearray | None, output_gltf.binary_blob())
    source_blob_hash = sha256(bytes(source_blob or b"")).hexdigest()
    output_blob_hash = sha256(bytes(output_blob or b"")).hexdigest()
    binary_preserved = (
        source_blob_hash == output_blob_hash
        if not append_only_geometry
        else bytes(output_blob or b"").startswith(bytes(source_blob or b""))
    )
    checks.append(
        _check(
            "BINARY_PAYLOAD_PRESERVED",
            binary_preserved,
            (
                "The source binary payload is an unchanged prefix of append-only authorized "
                "geometry data."
                if append_only_geometry
                else (
                    "The complete embedded binary payload, including geometry and images, is "
                    "unchanged."
                )
            ),
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

    expected_node_count = len(source_nodes) + (
        1 if normalization is not None and normalization.application_mode == "ADD_ROOT" else 0
    )
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
        payload = normalization
        if not output_nodes:
            root_change_valid = False
        elif payload.application_mode == "COMPOSE_EXISTING_ROOT":
            root_index = payload.existing_root_index
            after_matrix = payload.existing_root_after_matrix
            root_change_valid = (
                root_index is not None
                and after_matrix is not None
                and source_roots == output_roots == (root_index,)
                and np.allclose(
                    node_local_matrix(output_gltf.nodes[root_index]),
                    np.asarray(after_matrix, dtype=np.float64),
                    rtol=0.0,
                    atol=1e-12,
                )
            )
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
        expected_root_index = (
            payload.existing_root_index
            if payload.application_mode == "COMPOSE_EXISTING_ROOT"
            else len(output_nodes) - 1
        )
        actual_root_available = expected_root_index is not None and 0 <= expected_root_index < len(
            output_gltf.nodes
        )
        expected_children = (
            list(source_gltf.nodes[expected_root_index].children or ())
            if payload.application_mode == "COMPOSE_EXISTING_ROOT"
            and expected_root_index is not None
            and 0 <= expected_root_index < len(source_gltf.nodes)
            else list(source_roots)
        )
        root_expected = cast(
            JsonValue,
            {
                "scene_roots": [expected_root_index],
                "normalization_children": expected_children,
                "matrix": np.asarray(
                    payload.existing_root_after_matrix
                    if payload.application_mode == "COMPOSE_EXISTING_ROOT"
                    else payload.proposed_matrix,
                    dtype=np.float64,
                ).tolist(),
            },
        )
        root_actual = cast(
            JsonValue,
            {
                "scene_roots": list(output_roots),
                "normalization_children": (
                    list(output_gltf.nodes[expected_root_index].children or ())
                    if actual_root_available and expected_root_index is not None
                    else []
                ),
                "matrix": (
                    node_local_matrix(output_gltf.nodes[expected_root_index]).tolist()
                    if actual_root_available and expected_root_index is not None
                    else None
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
    if plan.planning_authority == "AGENT_ORCHESTRATED":
        semantic_codes = {"HEIGHT_OUT_OF_RANGE", "ORIENTATION_NOT_Y_UP", "NOT_GROUNDED"}
        output = output.model_copy(
            update={
                "findings": tuple(
                    finding for finding in output.findings if finding.code not in semantic_codes
                )
            }
        )
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
        weld = _executed_weld(plan, outcome)
        cleanup = _executed_degenerate_cleanup(plan, outcome)
        component_removal = _executed_component_removal(plan, outcome)
        expected_vertex_count = (
            original.geometry.vertex_count
            - (
                sum(primitive.merge_count for primitive in weld.primitives)
                if weld is not None
                else 0
            )
            - (
                sum(primitive.removed_unused_position_count for primitive in cleanup.primitives)
                if cleanup is not None
                else 0
            )
        )
        expected_triangle_count = (
            original.geometry.triangle_count
            - (
                sum(primitive.removed_degenerate_triangle_count for primitive in cleanup.primitives)
                if cleanup is not None
                else 0
            )
            - (
                sum(primitive.removed_triangle_count for primitive in component_removal.primitives)
                if component_removal is not None
                else 0
            )
        )
        count_pairs = (
            (
                "VERTEX_COUNT_PRESERVED",
                expected_vertex_count,
                output.geometry.vertex_count,
            ),
            (
                "TRIANGLE_COUNT_PRESERVED",
                expected_triangle_count,
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
        if weld is not None:
            output_primitives = (
                {
                    (primitive.mesh_index, primitive.primitive_index): primitive
                    for primitive in output.diagnostics.primitives
                }
                if output.diagnostics is not None
                else {}
            )
            remaining_safe_merges = {
                f"{primitive.mesh_index}:{primitive.primitive_index}": (
                    output_primitives[
                        (primitive.mesh_index, primitive.primitive_index)
                    ].attribute_safe_merge_count
                    if (primitive.mesh_index, primitive.primitive_index) in output_primitives
                    else None
                )
                for primitive in weld.primitives
            }
            checks.append(
                _check(
                    "ATTRIBUTE_SAFE_WELD_EXHAUSTED",
                    all(value == 0 for value in remaining_safe_merges.values()),
                    "Every selected primitive has no remaining byte-identical vertex tuples.",
                    expected=0,
                    actual=cast(JsonValue, remaining_safe_merges),
                )
            )
        if cleanup is not None:
            output_primitives = (
                {
                    (primitive.mesh_index, primitive.primitive_index): primitive
                    for primitive in output.diagnostics.primitives
                }
                if output.diagnostics is not None
                else {}
            )
            remaining = {
                f"{primitive.mesh_index}:{primitive.primitive_index}": {
                    "degenerate_triangles": (
                        output_primitives[
                            (primitive.mesh_index, primitive.primitive_index)
                        ].degenerate_triangle_count
                        if (primitive.mesh_index, primitive.primitive_index) in output_primitives
                        else None
                    ),
                    "unused_positions": (
                        output_primitives[
                            (primitive.mesh_index, primitive.primitive_index)
                        ].unused_position_count
                        if (primitive.mesh_index, primitive.primitive_index) in output_primitives
                        else None
                    ),
                }
                for primitive in cleanup.primitives
            }
            checks.append(
                _check(
                    "DEGENERATE_GEOMETRY_CLEANUP_CONFIRMED",
                    all(
                        values["degenerate_triangles"] == 0 and values["unused_positions"] == 0
                        for values in remaining.values()
                    ),
                    "Every selected primitive has no degenerate triangles or unreferenced vertex "
                    "tuples remaining.",
                    expected=cast(
                        JsonValue,
                        {"degenerate_triangles": 0, "unused_positions": 0},
                    ),
                    actual=cast(JsonValue, remaining),
                )
            )
        if component_removal is not None:
            output_primitives = (
                {
                    (primitive.mesh_index, primitive.primitive_index): primitive
                    for primitive in output.diagnostics.primitives
                }
                if output.diagnostics is not None
                else {}
            )
            expected_components = {
                f"{primitive.mesh_index}:{primitive.primitive_index}": len(
                    primitive.retained_component_ids
                )
                for primitive in component_removal.primitives
            }
            actual_components = {
                key: output_primitives[
                    (primitive.mesh_index, primitive.primitive_index)
                ].virtual_weld_connected_component_count
                if (primitive.mesh_index, primitive.primitive_index) in output_primitives
                else -1
                for key, primitive in (
                    (
                        f"{item.mesh_index}:{item.primitive_index}",
                        item,
                    )
                    for item in component_removal.primitives
                )
            }
            checks.append(
                _check(
                    "DISCONNECTED_COMPONENT_REMOVAL_CONFIRMED",
                    expected_components == actual_components,
                    "Fresh inspection confirms only the approved component selection remains.",
                    expected=cast(JsonValue, expected_components),
                    actual=cast(JsonValue, actual_components),
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
            independent_bounds = _trimesh_referenced_bounds(independent)
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
            if plan.planning_authority == "AGENT_ORCHESTRATED":
                expected_bounds = np.asarray(
                    [
                        normalization_payload.expected_after_bounds.minimum_m,
                        normalization_payload.expected_after_bounds.maximum_m,
                    ],
                    dtype=np.float64,
                )
                actual_bounds = np.asarray(
                    [output.geometry.bounds.minimum_m, output.geometry.bounds.maximum_m],
                    dtype=np.float64,
                )
                checks.append(
                    _check(
                        "AGENT_ACTION_BOUNDS_MATCH_PREVIEW",
                        np.allclose(actual_bounds, expected_bounds, rtol=1e-7, atol=1e-8),
                        "The executed physical action exactly matches its approved preview bounds.",
                        expected=cast(JsonValue, expected_bounds.tolist()),
                        actual=cast(JsonValue, actual_bounds.tolist()),
                    )
                )
            else:
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
                            expected=cast(
                                JsonValue,
                                {"target_cm": target, "tolerance_cm": tolerance},
                            ),
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
            if "pivot" in component_names:
                output_bounds = output.geometry.bounds
                if normalization_payload.pivot_target == "BOUNDS_CENTER":
                    actual_anchor = [
                        (output_bounds.minimum_m[index] + output_bounds.maximum_m[index]) / 2.0
                        for index in range(3)
                    ]
                    pivot_label = "world-bounds center"
                elif normalization_payload.pivot_target == "FOOTPRINT_CENTER_BOTTOM":
                    actual_anchor = [
                        (output_bounds.minimum_m[0] + output_bounds.maximum_m[0]) / 2.0,
                        output_bounds.minimum_m[1],
                        (output_bounds.minimum_m[2] + output_bounds.maximum_m[2]) / 2.0,
                    ]
                    pivot_label = "footprint center-bottom"
                elif normalization_payload.pivot_target == "MEASURED_ANCHOR":
                    if (
                        normalization_payload.pivot_anchor_position_m is None
                        or normalization_payload.pivot_anchor_label is None
                    ):
                        raise ValueError("Measured pivot payload has no registered anchor evidence")
                    source_anchor = np.asarray(
                        [*normalization_payload.pivot_anchor_position_m, 1.0],
                        dtype=np.float64,
                    )
                    transformed_anchor = (
                        np.asarray(normalization_payload.proposed_matrix, dtype=np.float64)
                        @ source_anchor
                    )[:3]
                    actual_anchor = transformed_anchor.tolist()
                    pivot_label = normalization_payload.pivot_anchor_label
                else:
                    raise ValueError("Pivot component has no bounded pivot target")
                checks.append(
                    _check(
                        "APPROVED_PIVOT_AT_TARGET",
                        np.allclose(actual_anchor, [0.0, 0.0, 0.0], rtol=0.0, atol=1e-8),
                        f"Approved pivot placement puts the {pivot_label} at the asset origin.",
                        expected=cast(JsonValue, [0.0, 0.0, 0.0]),
                        actual=cast(JsonValue, actual_anchor),
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
    if plan.planning_authority == "AGENT_ORCHESTRATED":
        second_plan_candidate_count = 0
        checks.append(
            _check(
                "NO_HIDDEN_DETERMINISTIC_REPLANNING",
                True,
                "Verification did not manufacture a target-dependent follow-up repair.",
                expected="fresh agent reassessment for any further action",
                actual="no deterministic variable plan",
            )
        )
    else:
        second_plan = plan_repairs(
            output,
            profile,
            excluded_candidate_ids=rejected_ids,
        )
        second_plan_candidate_count = len(second_plan.candidates)
        checks.append(
            _check(
                "SECOND_PLAN_EMPTY",
                not second_plan.candidates,
                "A second version-1 planning pass proposes no non-rejected repairs.",
                basis=CheckBasis.FROZEN_PROJECT_POLICY,
                expected=0,
                actual=second_plan_candidate_count,
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
        second_plan_candidate_count=second_plan_candidate_count,
    )
