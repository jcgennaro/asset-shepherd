"""Deterministic, facts-first GLB inspection."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import re
from base64 import b64decode
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Final, cast
from urllib.parse import unquote_to_bytes

import numpy as np
from PIL import Image as PillowImage
from pydantic import JsonValue
from pygltflib import GLTF2, Node

from asset_shepherd.glb import (
    GlbError,
    geometry_counts,
    load_glb,
    node_local_matrix,
    validate_loaded_glb,
    world_bounds,
)
from asset_shepherd.models import (
    ActionClass,
    Bounds3D,
    Finding,
    FindingEvidence,
    GeometryFacts,
    InspectionResult,
    NamingFacts,
    NodeHierarchyFact,
    NodeTransformFact,
    PackageFacts,
    ProjectProfile,
    RepairEligibility,
    ResourceFacts,
    Severity,
    TextureFact,
    TransformFacts,
)

SUPPORTED_REQUIRED_EXTENSIONS: Final[frozenset[str]] = frozenset()
_IDENTITY: Final = np.eye(4, dtype=np.float64)


def _bounds_model(minimum: np.ndarray, maximum: np.ndarray) -> Bounds3D:
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


def _package_facts(
    gltf: GLTF2,
    *,
    file_sha256: str,
    byte_size: int,
    parse_success: bool = True,
) -> PackageFacts:
    return PackageFacts(
        file_sha256=file_sha256,
        byte_size=byte_size,
        asset_version=gltf.asset.version,
        generator=gltf.asset.generator,
        parse_success=parse_success,
        scene_count=len(gltf.scenes),
        active_scene=cast(int | None, gltf.scene),
        node_count=len(gltf.nodes),
        mesh_count=len(gltf.meshes),
        primitive_count=sum(len(mesh.primitives) for mesh in gltf.meshes),
        material_count=len(gltf.materials),
        texture_count=len(gltf.textures),
        image_count=len(gltf.images),
        skin_count=len(gltf.skins),
        animation_count=len(gltf.animations),
        camera_count=len(gltf.cameras),
        extensions_used=tuple(sorted(gltf.extensionsUsed)),
        extensions_required=tuple(sorted(gltf.extensionsRequired)),
        has_morph_targets=any(
            bool(primitive.targets) for mesh in gltf.meshes for primitive in mesh.primitives
        ),
    )


def _empty_package_facts(file_sha256: str, byte_size: int) -> PackageFacts:
    return PackageFacts(
        file_sha256=file_sha256,
        byte_size=byte_size,
        asset_version=None,
        generator=None,
        parse_success=False,
        scene_count=0,
        active_scene=None,
        node_count=0,
        mesh_count=0,
        primitive_count=0,
        material_count=0,
        texture_count=0,
        image_count=0,
        skin_count=0,
        animation_count=0,
        camera_count=0,
        extensions_used=(),
        extensions_required=(),
        has_morph_targets=False,
    )


def _quaternion_from_rotation(rotation: np.ndarray) -> tuple[float, float, float, float]:
    trace = float(np.trace(rotation))
    if trace > 0:
        scale = np.sqrt(trace + 1.0) * 2.0
        quaternion = (
            (rotation[2, 1] - rotation[1, 2]) / scale,
            (rotation[0, 2] - rotation[2, 0]) / scale,
            (rotation[1, 0] - rotation[0, 1]) / scale,
            0.25 * scale,
        )
    else:
        diagonal = np.diag(rotation)
        index = int(np.argmax(diagonal))
        if index == 0:
            scale = np.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
            quaternion = (
                0.25 * scale,
                (rotation[0, 1] + rotation[1, 0]) / scale,
                (rotation[0, 2] + rotation[2, 0]) / scale,
                (rotation[2, 1] - rotation[1, 2]) / scale,
            )
        elif index == 1:
            scale = np.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
            quaternion = (
                (rotation[0, 1] + rotation[1, 0]) / scale,
                0.25 * scale,
                (rotation[1, 2] + rotation[2, 1]) / scale,
                (rotation[0, 2] - rotation[2, 0]) / scale,
            )
        else:
            scale = np.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
            quaternion = (
                (rotation[0, 2] + rotation[2, 0]) / scale,
                (rotation[1, 2] + rotation[2, 1]) / scale,
                0.25 * scale,
                (rotation[1, 0] - rotation[0, 1]) / scale,
            )
    return (
        float(quaternion[0]),
        float(quaternion[1]),
        float(quaternion[2]),
        float(quaternion[3]),
    )


def _decompose_node(
    node: Node,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float],
    float,
]:
    local = node_local_matrix(node)
    linear = local[:3, :3]
    determinant = float(np.linalg.det(linear))
    scales = np.linalg.norm(linear, axis=0)
    if np.any(scales <= 1e-12):
        rotation = np.eye(3, dtype=np.float64)
    else:
        rotation = linear / scales
        if np.linalg.det(rotation) < 0:
            scales[0] *= -1
            rotation[:, 0] *= -1
    translation = (float(local[0, 3]), float(local[1, 3]), float(local[2, 3]))
    scale = (float(scales[0]), float(scales[1]), float(scales[2]))
    return translation, _quaternion_from_rotation(rotation), scale, determinant


def _transform_facts(gltf: GLTF2) -> TransformFacts:
    if not gltf.scenes:
        raise GlbError("GLB has no scenes")
    configured_scene = cast(int | None, gltf.scene)
    scene_index = configured_scene if configured_scene is not None else 0
    roots = tuple(gltf.scenes[scene_index].nodes or [])
    parents: dict[int, int] = {}
    for parent_index, node in enumerate(gltf.nodes):
        for child_index in node.children or []:
            parents.setdefault(child_index, parent_index)

    transform_facts: list[NodeTransformFact] = []
    negative_nodes: list[int] = []
    non_uniform_nodes: list[int] = []
    for node_index, node in enumerate(gltf.nodes):
        local = node_local_matrix(node)
        if np.allclose(local, _IDENTITY, rtol=0.0, atol=1e-9):
            continue
        translation, rotation, scale, determinant = _decompose_node(node)
        magnitudes = np.abs(np.asarray(scale))
        non_uniform = not np.allclose(magnitudes, magnitudes[0], rtol=1e-6, atol=1e-9)
        negative = determinant < 0
        if non_uniform:
            non_uniform_nodes.append(node_index)
        if negative:
            negative_nodes.append(node_index)
        transform_facts.append(
            NodeTransformFact(
                node_index=node_index,
                node_name=node.name,
                translation=translation,
                rotation=rotation,
                scale=scale,
                determinant=determinant,
                non_uniform_scale=non_uniform,
                negative_determinant=negative,
            )
        )

    hierarchy = tuple(
        NodeHierarchyFact(
            node_index=index,
            parent_index=parents.get(index),
            child_indices=tuple(node.children or []),
        )
        for index, node in enumerate(gltf.nodes)
    )
    return TransformFacts(
        root_nodes=roots,
        non_identity_transforms=tuple(transform_facts),
        negative_determinant_nodes=tuple(negative_nodes),
        non_uniform_scale_nodes=tuple(non_uniform_nodes),
        hierarchy=hierarchy,
    )


def _unique_replacement(prefix: str, index: int, reserved: set[str]) -> str:
    candidate = f"{prefix}_{index:03d}"
    suffix = 1
    while candidate in reserved:
        candidate = f"{prefix}_{index:03d}_{suffix:02d}"
        suffix += 1
    reserved.add(candidate)
    return candidate


def _naming_facts(gltf: GLTF2, profile: ProjectProfile) -> NamingFacts:
    pattern = re.compile(profile.naming.pattern)
    node_names = [node.name for node in gltf.nodes]
    mesh_names = [mesh.name for mesh in gltf.meshes]

    def classify(
        names: list[str | None],
        *,
        prefix: str,
    ) -> tuple[tuple[int, ...], tuple[int, ...], dict[str, tuple[int, ...]], dict[str, str]]:
        missing = tuple(index for index, name in enumerate(names) if not name)
        invalid = tuple(
            index
            for index, name in enumerate(names)
            if name is not None and bool(name) and pattern.fullmatch(name) is None
        )
        occurrences: defaultdict[str, list[int]] = defaultdict(list)
        for index, name in enumerate(names):
            if name:
                occurrences[name].append(index)
        duplicates = {
            name: tuple(indices)
            for name, indices in sorted(occurrences.items())
            if len(indices) > 1
        }
        duplicate_indices = {index for indices in duplicates.values() for index in indices[1:]}
        repair_indices = set(missing) | set(invalid) | duplicate_indices
        reserved = {
            name
            for index, name in enumerate(names)
            if name and index not in repair_indices and pattern.fullmatch(name)
        }
        replacements = {
            f"{prefix.lower()}:{index}": _unique_replacement(prefix, index, reserved)
            for index in sorted(repair_indices)
        }
        return missing, invalid, duplicates, replacements

    missing_nodes, invalid_nodes, duplicate_nodes, node_replacements = classify(
        node_names,
        prefix="Node",
    )
    missing_meshes, invalid_meshes, duplicate_meshes, mesh_replacements = classify(
        mesh_names,
        prefix="Mesh",
    )
    return NamingFacts(
        missing_node_indices=missing_nodes,
        invalid_node_indices=invalid_nodes,
        duplicate_node_names=duplicate_nodes,
        missing_mesh_indices=missing_meshes,
        invalid_mesh_indices=invalid_meshes,
        duplicate_mesh_names=duplicate_meshes,
        proposed_replacements={**node_replacements, **mesh_replacements},
    )


def _image_bytes(gltf: GLTF2, image_index: int) -> tuple[bytes | None, str | None]:
    image = gltf.images[image_index]
    buffer_view_index = cast(int | None, image.bufferView)
    if buffer_view_index is not None:
        if not 0 <= buffer_view_index < len(gltf.bufferViews):
            return None, "Image references an invalid buffer view"
        view = gltf.bufferViews[buffer_view_index]
        blob = cast(bytes | bytearray | None, gltf.binary_blob())
        if blob is None:
            return None, "GLB has no binary chunk"
        start = view.byteOffset or 0
        end = start + view.byteLength
        if start < 0 or end > len(blob):
            return None, "Image buffer view exceeds the binary chunk"
        return bytes(blob[start:end]), None
    uri = cast(str | None, image.uri)
    if not uri:
        return None, "Image has neither a buffer view nor URI"
    if not uri.startswith("data:"):
        return None, "External image URIs are not fetched"
    try:
        header, payload = uri.split(",", maxsplit=1)
        if ";base64" in header:
            data = b64decode(payload, validate=True)
        else:
            data = unquote_to_bytes(payload)
    except (ValueError, TypeError) as error:
        return None, f"Invalid image data URI: {error}"
    return data, None


def _resource_facts(gltf: GLTF2, profile: ProjectProfile) -> ResourceFacts:
    textures: list[TextureFact] = []
    budget_violations: list[str] = []
    for index, image in enumerate(gltf.images):
        data, detail = _image_bytes(gltf, index)
        width: int | None = None
        height: int | None = None
        readable = False
        detected_format: str | None = image.mimeType
        if data is not None:
            try:
                with PillowImage.open(BytesIO(data)) as opened:
                    width, height = opened.size
                    detected_format = opened.format or detected_format
                    opened.verify()
                readable = True
            except (OSError, ValueError) as error:
                detail = f"Embedded image is unreadable: {error}"
        textures.append(
            TextureFact(
                image_index=index,
                name=image.name,
                mime_type=detected_format,
                width=width,
                height=height,
                readable=readable,
                detail=detail,
            )
        )
        if width is not None and height is not None:
            if max(width, height) > profile.budgets.max_texture_dimension:
                budget_violations.append(f"image:{index}:dimension")
    if len(gltf.materials) > profile.budgets.max_materials:
        budget_violations.append("materials:count")
    if len(gltf.textures) > profile.budgets.max_textures:
        budget_violations.append("textures:count")
    return ResourceFacts(
        material_count=len(gltf.materials),
        texture_count=len(gltf.textures),
        image_count=len(gltf.images),
        textures=tuple(textures),
        budget_violations=tuple(budget_violations),
    )


def _finding(
    *,
    code: str,
    domain: str,
    title: str,
    description: str,
    severity: Severity,
    action_class: ActionClass,
    confidence: float,
    affected: tuple[str, ...],
    evidence: tuple[FindingEvidence, ...],
    profile_rule: str | None,
    candidates: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        id=f"finding-{code.lower().replace('_', '-')}",
        code=code,
        domain=domain,
        title=title,
        description=description,
        severity=severity,
        action_class=action_class,
        confidence=confidence,
        affected_components=affected,
        evidence=evidence,
        profile_rule=profile_rule,
        candidate_repairs=candidates,
    )


def _naming_findings(naming: NamingFacts) -> list[Finding]:
    findings: list[Finding] = []
    categories = (
        (
            "NODE_NAME_MISSING",
            naming.missing_node_indices,
            "Nodes are missing names",
            "node",
        ),
        (
            "NODE_NAME_INVALID",
            naming.invalid_node_indices,
            "Node names violate the project pattern",
            "node",
        ),
        (
            "NODE_NAME_DUPLICATE",
            tuple(index for indices in naming.duplicate_node_names.values() for index in indices),
            "Node names are not unique",
            "node",
        ),
        (
            "MESH_NAME_MISSING",
            naming.missing_mesh_indices,
            "Meshes are missing names",
            "mesh",
        ),
        (
            "MESH_NAME_INVALID",
            naming.invalid_mesh_indices,
            "Mesh names violate the project pattern",
            "mesh",
        ),
        (
            "MESH_NAME_DUPLICATE",
            tuple(index for indices in naming.duplicate_mesh_names.values() for index in indices),
            "Mesh names are not unique",
            "mesh",
        ),
    )
    for code, indices, title, component_type in categories:
        if not indices:
            continue
        candidate_ids = tuple(
            f"rename-{component_type}-{index:03d}"
            for index in sorted(set(indices))
            if f"{component_type}:{index}" in naming.proposed_replacements
        )
        findings.append(
            _finding(
                code=code,
                domain="naming",
                title=title,
                description="Display names can be normalized without changing index references.",
                severity=Severity.ERROR,
                action_class=ActionClass.AUTO_SAFE,
                confidence=1.0,
                affected=tuple(f"{component_type}:{index}" for index in sorted(set(indices))),
                evidence=(
                    FindingEvidence(
                        observation=f"Affected {component_type} indices: {sorted(set(indices))}",
                        observed_value=list(sorted(set(indices))),
                        inference=(
                            "Deterministic valid unique names can replace these display names."
                        ),
                    ),
                ),
                profile_rule=f"naming.{component_type}_names",
                candidates=candidate_ids,
            )
        )
    return findings


def _inspection_findings(
    gltf: GLTF2,
    profile: ProjectProfile,
    geometry: GeometryFacts,
    transforms: TransformFacts,
    naming: NamingFacts,
    resources: ResourceFacts,
) -> tuple[list[Finding], RepairEligibility]:
    findings: list[Finding] = []
    unsupported_features: list[str] = []
    if gltf.skins:
        unsupported_features.append("skins")
    if gltf.animations:
        unsupported_features.append("animations")
    if any(bool(primitive.targets) for mesh in gltf.meshes for primitive in mesh.primitives):
        unsupported_features.append("morph targets")
    unsupported_required = sorted(set(gltf.extensionsRequired) - SUPPORTED_REQUIRED_EXTENSIONS)
    if unsupported_required:
        unsupported_features.append(f"required extensions: {', '.join(unsupported_required)}")
    eligibility = RepairEligibility.ELIGIBLE_STATIC_MESH
    if unsupported_features:
        eligibility = RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES
        findings.append(
            _finding(
                code="UNSUPPORTED_REPAIR_FEATURES",
                domain="structure",
                title="Asset contains inspection-only features",
                description="The asset can be inspected but structural repair is blocked.",
                severity=Severity.BLOCKER,
                action_class=ActionClass.BLOCKED,
                confidence=1.0,
                affected=tuple(unsupported_features),
                evidence=(
                    FindingEvidence(
                        observation="; ".join(unsupported_features),
                        inference="Version-1 repair cannot prove these semantics remain intact.",
                    ),
                ),
                profile_rule=None,
            )
        )

    dominant_index = {"X": 0, "Y": 1, "Z": 2}[geometry.dominant_dimension_axis]
    inferred_height_cm = geometry.bounds.dimensions_cm[dominant_index]
    target = profile.expected_height_cm.target
    tolerance = profile.expected_height_cm.tolerance
    if abs(inferred_height_cm - target) > tolerance:
        findings.append(
            _finding(
                code="HEIGHT_OUT_OF_RANGE",
                domain="geometry",
                title="Physical size is outside the project tolerance",
                description="The dominant measured extent does not match the target asset height.",
                severity=Severity.ERROR,
                action_class=ActionClass.APPROVAL_REQUIRED,
                confidence=0.99,
                affected=("active_scene",),
                evidence=(
                    FindingEvidence(
                        observation=f"Dominant extent is {inferred_height_cm:.6g} cm.",
                        observed_value=inferred_height_cm,
                        expected_value={"target_cm": target, "tolerance_cm": tolerance},
                        inference=(
                            f"A scale factor of {target / inferred_height_cm:.9g} reaches "
                            "target height."
                        ),
                        units="centimeters",
                    ),
                ),
                profile_rule="expected_height_cm",
                candidates=("normalize-root-v1",),
            )
        )
    if profile.orientation.require_y_up_geometry and geometry.dominant_dimension_axis != "Y":
        orientation_observation = (
            f"Dominant world-space axis is {geometry.dominant_dimension_axis}."
        )
        findings.append(
            _finding(
                code="ORIENTATION_NOT_Y_UP",
                domain="geometry",
                title="Dominant vertical extent is not on Y",
                description="The asset appears sideways relative to the glTF Y-up convention.",
                severity=Severity.ERROR,
                action_class=ActionClass.APPROVAL_REQUIRED,
                confidence=0.98,
                affected=("active_scene",),
                evidence=(
                    FindingEvidence(
                        observation=orientation_observation,
                        observed_value=geometry.dominant_dimension_axis,
                        expected_value="Y",
                        inference=(
                            "A right-handed axis rotation can map the dominant extent "
                            "to positive Y."
                        ),
                    ),
                ),
                profile_rule="orientation.require_y_up_geometry",
                candidates=("normalize-root-v1",),
            )
        )
    if profile.orientation.require_ground_contact and geometry.ground_relationship != "GROUNDED":
        findings.append(
            _finding(
                code="NOT_GROUNDED",
                domain="geometry",
                title="Asset does not meet the ground-contact rule",
                description="The lowest world-space point is outside the allowed Y=0 tolerance.",
                severity=Severity.ERROR,
                action_class=ActionClass.APPROVAL_REQUIRED,
                confidence=1.0,
                affected=("active_scene",),
                evidence=(
                    FindingEvidence(
                        observation=f"Minimum Y is {geometry.bounds.minimum_m[1]:.9g} m.",
                        observed_value=geometry.bounds.minimum_m[1],
                        expected_value={
                            "ground_y_m": 0.0,
                            "tolerance_cm": profile.orientation.ground_tolerance_cm,
                        },
                        inference="A translation can place the lowest point at Y=0.",
                        units="meters",
                    ),
                ),
                profile_rule="orientation.require_ground_contact",
                candidates=("normalize-root-v1",),
            )
        )

    findings.extend(_naming_findings(naming))
    if geometry.triangle_count > profile.budgets.max_triangles:
        findings.append(
            _finding(
                code="TRIANGLE_BUDGET_EXCEEDED",
                domain="budgets",
                title="Triangle budget exceeded",
                description="Version 1 reports topology budgets but does not alter topology.",
                severity=Severity.WARNING,
                action_class=ActionClass.REPORT_ONLY,
                confidence=1.0,
                affected=("geometry",),
                evidence=(
                    FindingEvidence(
                        observation=f"Triangle count is {geometry.triangle_count}.",
                        observed_value=geometry.triangle_count,
                        expected_value=profile.budgets.max_triangles,
                    ),
                ),
                profile_rule="budgets.max_triangles",
            )
        )
    budget_findings = (
        (
            "MATERIAL_BUDGET_EXCEEDED",
            resources.material_count,
            profile.budgets.max_materials,
            "material",
        ),
        (
            "TEXTURE_BUDGET_EXCEEDED",
            resources.texture_count,
            profile.budgets.max_textures,
            "texture",
        ),
    )
    for code, actual, maximum, resource_name in budget_findings:
        if actual <= maximum:
            continue
        findings.append(
            _finding(
                code=code,
                domain="budgets",
                title=f"{resource_name.title()} budget exceeded",
                description=(
                    f"Version 1 reports {resource_name} budgets but does not merge resources."
                ),
                severity=Severity.WARNING,
                action_class=ActionClass.REPORT_ONLY,
                confidence=1.0,
                affected=(f"{resource_name}s",),
                evidence=(
                    FindingEvidence(
                        observation=f"{resource_name.title()} count is {actual}.",
                        observed_value=actual,
                        expected_value=maximum,
                    ),
                ),
                profile_rule=f"budgets.max_{resource_name}s",
            )
        )
    oversized_images = [
        texture.image_index
        for texture in resources.textures
        if texture.width is not None
        and texture.height is not None
        and max(texture.width, texture.height) > profile.budgets.max_texture_dimension
    ]
    if oversized_images:
        findings.append(
            _finding(
                code="TEXTURE_DIMENSION_EXCEEDED",
                domain="budgets",
                title="Embedded image dimension budget exceeded",
                description="Version 1 does not resize or modify textures.",
                severity=Severity.WARNING,
                action_class=ActionClass.REPORT_ONLY,
                confidence=1.0,
                affected=tuple(f"image:{index}" for index in oversized_images),
                evidence=(
                    FindingEvidence(
                        observation=f"Oversized image indices: {oversized_images}",
                        observed_value=cast(JsonValue, oversized_images),
                        expected_value=profile.budgets.max_texture_dimension,
                        units="pixels",
                    ),
                ),
                profile_rule="budgets.max_texture_dimension",
            )
        )
    unreadable_images = [
        texture.image_index for texture in resources.textures if not texture.readable
    ]
    if unreadable_images:
        findings.append(
            _finding(
                code="IMAGE_UNREADABLE",
                domain="resources",
                title="One or more embedded images are unreadable",
                description="Unreadable image data is preserved but cannot be verified.",
                severity=Severity.WARNING,
                action_class=ActionClass.REPORT_ONLY,
                confidence=1.0,
                affected=tuple(f"image:{index}" for index in unreadable_images),
                evidence=(
                    FindingEvidence(
                        observation=f"Unreadable image indices: {unreadable_images}",
                        observed_value=cast(JsonValue, unreadable_images),
                    ),
                ),
                profile_rule=None,
            )
        )
    for code, indices, title in (
        (
            "NEGATIVE_DETERMINANT_TRANSFORM",
            transforms.negative_determinant_nodes,
            "Negative determinant transforms detected",
        ),
        (
            "NON_UNIFORM_SCALE_TRANSFORM",
            transforms.non_uniform_scale_nodes,
            "Non-uniform node scales detected",
        ),
    ):
        if indices:
            findings.append(
                _finding(
                    code=code,
                    domain="transforms",
                    title=title,
                    description=(
                        "Version 1 reports this transform and does not bake it into geometry."
                    ),
                    severity=Severity.WARNING,
                    action_class=ActionClass.REPORT_ONLY,
                    confidence=1.0,
                    affected=tuple(f"node:{index}" for index in indices),
                    evidence=(
                        FindingEvidence(
                            observation=f"Affected node indices: {list(indices)}",
                            observed_value=list(indices),
                        ),
                    ),
                    profile_rule=None,
                )
            )
    return findings, eligibility


def inspect_asset(path: Path, profile: ProjectProfile) -> InspectionResult:
    """Inspect a GLB deterministically without executing or fetching asset content."""
    try:
        source_bytes = path.read_bytes()
    except OSError as error:
        source_bytes = b""
        read_error: Exception | None = error
    else:
        read_error = None
    source_hash = sha256(source_bytes).hexdigest()
    inspection_id = f"inspection-{source_hash[:16]}-p{profile.profile_version}"
    try:
        if read_error is not None:
            raise GlbError(f"Could not read source file: {read_error}")
        gltf = load_glb(path)
        validate_loaded_glb(gltf)
        bounds = world_bounds(gltf)
        counts = geometry_counts(gltf)
        bounds_model = _bounds_model(bounds.minimum, bounds.maximum)
        dominant_axis = ("X", "Y", "Z")[int(np.argmax(bounds.dimensions))]
        tolerance_m = profile.orientation.ground_tolerance_cm / 100.0
        minimum_y = float(bounds.minimum[1])
        if minimum_y < -tolerance_m:
            ground = "EXTENDS_BELOW"
        elif minimum_y > tolerance_m:
            ground = "FLOATS_ABOVE"
        elif minimum_y < 0:
            ground = "INTERSECTS"
        else:
            ground = "GROUNDED"
        geometry = GeometryFacts(
            vertex_count=counts.vertices,
            triangle_count=counts.triangles,
            bounds=bounds_model,
            dominant_dimension_axis=dominant_axis,
            ground_relationship=ground,
        )
        transforms = _transform_facts(gltf)
        naming = _naming_facts(gltf, profile)
        resources = _resource_facts(gltf, profile)
        findings, eligibility = _inspection_findings(
            gltf,
            profile,
            geometry,
            transforms,
            naming,
            resources,
        )
        return InspectionResult(
            inspection_id=inspection_id,
            source_filename=path.name,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            package=_package_facts(
                gltf,
                file_sha256=source_hash,
                byte_size=len(source_bytes),
            ),
            geometry=geometry,
            transforms=transforms,
            naming=naming,
            resources=resources,
            repair_eligibility=eligibility,
            findings=tuple(sorted(findings, key=lambda finding: finding.code)),
        )
    except (GlbError, OSError, ValueError, IndexError, TypeError) as error:
        finding = _finding(
            code="INVALID_OR_UNREADABLE",
            domain="package",
            title="Asset is invalid or unreadable",
            description="Inspection could not safely parse and measure this file.",
            severity=Severity.BLOCKER,
            action_class=ActionClass.BLOCKED,
            confidence=1.0,
            affected=(path.name,),
            evidence=(FindingEvidence(observation=str(error)),),
            profile_rule=None,
        )
        return InspectionResult(
            inspection_id=inspection_id,
            source_filename=path.name,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            package=_empty_package_facts(source_hash, len(source_bytes)),
            geometry=None,
            transforms=None,
            naming=None,
            resources=None,
            repair_eligibility=RepairEligibility.INVALID_OR_UNREADABLE,
            findings=(finding,),
        )


def render_inspection_report(inspection: InspectionResult) -> str:
    """Render a concise human-readable inspection report from structured facts."""
    lines = [
        "# Asset Shepherd Inspection",
        "",
        f"- Source: `{inspection.source_filename}`",
        f"- SHA-256: `{inspection.package.file_sha256}`",
        f"- Repair eligibility: `{inspection.repair_eligibility}`",
    ]
    if inspection.geometry is not None:
        dimensions = inspection.geometry.bounds.dimensions_m
        lines.extend(
            (
                f"- Dimensions: {dimensions[0]:.6g} x {dimensions[1]:.6g} x "
                f"{dimensions[2]:.6g} meters",
                f"- Geometry: {inspection.geometry.vertex_count} vertices, "
                f"{inspection.geometry.triangle_count} triangles",
            )
        )
    lines.extend(("", "## Findings", ""))
    if not inspection.findings:
        lines.append("No project-policy findings.")
    else:
        lines.extend(("| Severity | Code | Finding | Action |", "|---|---|---|---|"))
        lines.extend(
            f"| {finding.severity} | `{finding.code}` | {finding.title} | {finding.action_class} |"
            for finding in inspection.findings
        )
    return "\n".join(lines) + "\n"
