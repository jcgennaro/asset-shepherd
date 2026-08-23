"""Deterministic, facts-first GLB inspection."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
import re
from base64 import b64decode
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Final, cast
from urllib.parse import unquote_to_bytes

import numpy as np
import numpy.typing as npt
from PIL import Image as PillowImage
from pydantic import JsonValue
from pygltflib import FLOAT, GLTF2, TRIANGLE_FAN, TRIANGLE_STRIP, TRIANGLES, Node

from asset_shepherd.glb import (
    GlbError,
    accessor_array,
    geometry_counts,
    iter_world_matrices,
    load_glb,
    node_local_matrix,
    validate_loaded_glb,
    world_bounds,
)
from asset_shepherd.models import (
    ActionClass,
    Bounds3D,
    CheckBasis,
    Finding,
    FindingEvidence,
    GeometryFacts,
    InspectionResult,
    MaterialFact,
    NamingFacts,
    NodeHierarchyFact,
    NodeTransformFact,
    PackageFacts,
    PreflightResult,
    PrimitiveAttributeDiagnostics,
    ProfilePolicyProvenance,
    ProjectProfile,
    RepairEligibility,
    ResourceFacts,
    Severity,
    SourceDiagnostics,
    TextureFact,
    TransformFacts,
)
from asset_shepherd.profile_policy import finding_rule_provenance

SUPPORTED_REQUIRED_EXTENSIONS: Final[frozenset[str]] = frozenset()
_IDENTITY: Final = np.eye(4, dtype=np.float64)


def _material_facts(gltf: GLTF2) -> tuple[MaterialFact, ...]:
    """Return only glTF-declared material values, without appearance inference."""
    facts: list[MaterialFact] = []
    for index, material in enumerate(gltf.materials):
        pbr = material.pbrMetallicRoughness
        base_color = tuple(
            float(value)
            for value in (
                pbr.baseColorFactor if pbr is not None and pbr.baseColorFactor else [1, 1, 1, 1]
            )
        )
        emissive = tuple(float(value) for value in (material.emissiveFactor or [0, 0, 0]))
        facts.append(
            MaterialFact(
                material_index=index,
                name=material.name,
                alpha_mode=material.alphaMode or "OPAQUE",
                alpha_cutoff=(
                    float(material.alphaCutoff) if material.alphaCutoff is not None else None
                ),
                double_sided=bool(material.doubleSided),
                base_color_factor=cast(tuple[float, float, float, float], base_color),
                metallic_factor=(
                    float(pbr.metallicFactor)
                    if pbr is not None and pbr.metallicFactor is not None
                    else 1.0
                ),
                roughness_factor=(
                    float(pbr.roughnessFactor)
                    if pbr is not None and pbr.roughnessFactor is not None
                    else 1.0
                ),
                emissive_factor=cast(tuple[float, float, float], emissive),
            )
        )
    return tuple(facts)


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
        require_unique: bool,
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
        duplicate_indices: set[int] = (
            {index for indices in duplicates.values() for index in indices[1:]}
            if require_unique
            else set[int]()
        )
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
        require_unique=profile.naming.require_unique_node_names,
    )
    missing_meshes, invalid_meshes, duplicate_meshes, mesh_replacements = classify(
        mesh_names,
        prefix="Mesh",
        require_unique=profile.naming.require_unique_mesh_names,
    )
    return NamingFacts(
        node_names=tuple(node_names),
        missing_node_indices=missing_nodes,
        invalid_node_indices=invalid_nodes,
        duplicate_node_names=duplicate_nodes,
        mesh_names=tuple(mesh_names),
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


def _attribute_accessor_index(attributes: object, name: str) -> int | None:
    value = getattr(attributes, name, None)
    return value if isinstance(value, int) else None


def _non_finite_count(values: np.ndarray) -> int:
    if not np.issubdtype(values.dtype, np.floating):
        return 0
    return int(np.count_nonzero(~np.isfinite(values)))


def _primitive_diagnostics(
    gltf: GLTF2,
    mesh_index: int,
    primitive_index: int,
) -> PrimitiveAttributeDiagnostics:
    primitive = gltf.meshes[mesh_index].primitives[primitive_index]
    position_index = _attribute_accessor_index(primitive.attributes, "POSITION")
    if position_index is None:
        raise GlbError("Mesh primitive has no POSITION accessor")
    positions = accessor_array(gltf, position_index)
    position_count = len(positions)
    normal_index = _attribute_accessor_index(primitive.attributes, "NORMAL")
    tangent_index = _attribute_accessor_index(primitive.attributes, "TANGENT")
    texcoord_index = _attribute_accessor_index(primitive.attributes, "TEXCOORD_0")

    mismatches: list[str] = []

    def attribute_values(accessor_index: int | None, semantic: str) -> np.ndarray | None:
        if accessor_index is None:
            return None
        values = accessor_array(gltf, accessor_index)
        if len(values) != position_count:
            mismatches.append(
                f"{semantic} count {len(values)} does not match POSITION count {position_count}"
            )
        return values

    normals = attribute_values(normal_index, "NORMAL")
    tangents = attribute_values(tangent_index, "TANGENT")
    texcoords = attribute_values(texcoord_index, "TEXCOORD_0")

    indices: npt.NDArray[np.int64]
    if primitive.indices is None:
        indices = np.arange(position_count, dtype=np.int64)
    else:
        indices = np.asarray(
            accessor_array(gltf, primitive.indices),
            dtype=np.int64,
        ).reshape(-1)
    out_of_range = (indices < 0) | (indices >= position_count)

    mode = primitive.mode if primitive.mode is not None else TRIANGLES
    if mode == TRIANGLES:
        usable = len(indices) - (len(indices) % 3)
        triangles = indices[:usable].reshape((-1, 3))
    elif mode == TRIANGLE_STRIP and len(indices) >= 3:
        triangles = np.column_stack((indices[:-2], indices[1:-1], indices[2:]))
    elif mode == TRIANGLE_FAN and len(indices) >= 3:
        triangles = np.column_stack(
            (
                np.full(len(indices) - 2, indices[0], dtype=indices.dtype),
                indices[1:-1],
                indices[2:],
            )
        )
    else:
        triangles = np.empty((0, 3), dtype=np.int64)
    repeated_indices = (
        (triangles[:, 0] == triangles[:, 1])
        | (triangles[:, 1] == triangles[:, 2])
        | (triangles[:, 0] == triangles[:, 2])
    )
    degenerate = repeated_indices.copy()
    valid_triangles = ~np.any(
        (triangles < 0) | (triangles >= position_count),
        axis=1,
    )
    valid_non_repeated = valid_triangles & ~repeated_indices
    if np.any(valid_non_repeated):
        triangle_positions = positions[triangles[valid_non_repeated], :3].astype(
            np.float64,
            copy=False,
        )
        finite_triangles = np.isfinite(triangle_positions).all(axis=(1, 2))
        twice_area = np.full(len(triangle_positions), np.inf, dtype=np.float64)
        finite_positions = triangle_positions[finite_triangles]
        twice_area[finite_triangles] = np.linalg.norm(
            np.cross(
                finite_positions[:, 1] - finite_positions[:, 0],
                finite_positions[:, 2] - finite_positions[:, 0],
            ),
            axis=1,
        )
        finite_source_positions = positions[np.isfinite(positions).all(axis=1), :3]
        if len(finite_source_positions):
            extent = np.ptp(finite_source_positions.astype(np.float64, copy=False), axis=0)
            scale_squared = max(float(np.dot(extent, extent)), 1.0)
        else:
            scale_squared = 1.0
        area_tolerance = np.finfo(np.float64).eps * scale_squared * 64.0
        area_degenerate = twice_area <= area_tolerance
        degenerate[np.flatnonzero(valid_non_repeated)] = area_degenerate

    non_unit_normals = 0
    normal_accessor = gltf.accessors[normal_index] if normal_index is not None else None
    if (
        normals is not None
        and normal_accessor is not None
        and normal_accessor.componentType == FLOAT
    ):
        finite_rows = np.isfinite(normals).all(axis=1)
        lengths = np.linalg.norm(normals[finite_rows, :3], axis=1)
        non_unit_normals = int(np.count_nonzero(~np.isclose(lengths, 1.0, atol=1e-3)))

    invalid_handedness = 0
    if tangents is not None and tangents.shape[1] >= 4:
        finite_w = tangents[:, 3][np.isfinite(tangents[:, 3])]
        invalid_handedness = int(np.count_nonzero(~np.isclose(np.abs(finite_w), 1.0, atol=1e-6)))

    return PrimitiveAttributeDiagnostics(
        mesh_index=mesh_index,
        primitive_index=primitive_index,
        position_count=position_count,
        index_count=len(indices),
        has_normals=normals is not None,
        has_tangents=tangents is not None,
        has_texcoord_0=texcoords is not None,
        attribute_count_mismatches=tuple(mismatches),
        non_finite_position_count=_non_finite_count(positions),
        non_finite_normal_count=0 if normals is None else _non_finite_count(normals),
        non_unit_normal_count=non_unit_normals,
        non_finite_tangent_count=0 if tangents is None else _non_finite_count(tangents),
        invalid_tangent_handedness_count=invalid_handedness,
        non_finite_texcoord_0_count=0 if texcoords is None else _non_finite_count(texcoords),
        out_of_range_index_count=int(np.count_nonzero(out_of_range)),
        degenerate_triangle_count=int(np.count_nonzero(degenerate)),
    )


def _canonical_resource_key(value: object) -> str:
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        value = {key: item for key, item in mapping.items() if key != "name"}
    return json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _duplicate_groups(values: list[object]) -> tuple[tuple[int, ...], ...]:
    grouped: defaultdict[str, list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        grouped[_canonical_resource_key(value)].append(index)
    return tuple(tuple(indices) for _, indices in sorted(grouped.items()) if len(indices) > 1)


def _material_texture_indices(material: object) -> set[int]:
    indices: set[int] = set()

    def walk(value: object, parent_key: str | None = None) -> None:
        if isinstance(value, dict):
            mapping = cast(dict[str, object], value)
            index = mapping.get("index")
            if (
                parent_key is not None
                and "texture" in parent_key.lower()
                and isinstance(index, int)
            ):
                indices.add(index)
            for key, child in mapping.items():
                walk(child, key)
        elif isinstance(value, list):
            for child in cast(list[object], value):
                walk(child, parent_key)

    walk(material)
    return indices


def _source_diagnostics(gltf: GLTF2, geometry: GeometryFacts) -> SourceDiagnostics:
    primitives = tuple(
        _primitive_diagnostics(gltf, mesh_index, primitive_index)
        for mesh_index, mesh in enumerate(gltf.meshes)
        for primitive_index, _ in enumerate(mesh.primitives)
    )
    reachable_nodes = {node_index for node_index, _ in iter_world_matrices(gltf)}
    used_meshes: set[int] = set()
    for node_index in reachable_nodes:
        mesh_index = gltf.nodes[node_index].mesh
        if mesh_index is not None:
            used_meshes.add(mesh_index)
    used_materials: set[int] = set()
    for mesh_index in used_meshes:
        for primitive in gltf.meshes[mesh_index].primitives:
            material_index = primitive.material
            if material_index is not None:
                used_materials.add(material_index)
    document = cast(dict[str, object], json.loads(gltf.to_json()))
    materials_value = document.get("materials", [])
    material_dicts = cast(list[object], materials_value)
    used_textures: set[int] = set()
    for material_index in used_materials:
        used_textures.update(_material_texture_indices(material_dicts[material_index]))
    used_images = {
        gltf.textures[index].source
        for index in used_textures
        if 0 <= index < len(gltf.textures) and isinstance(gltf.textures[index].source, int)
    }
    used_samplers = {
        gltf.textures[index].sampler
        for index in used_textures
        if 0 <= index < len(gltf.textures) and isinstance(gltf.textures[index].sampler, int)
    }
    empty_leaf_nodes = tuple(
        index
        for index, node in enumerate(gltf.nodes)
        if not node.children and node.mesh is None and node.camera is None and node.skin is None
    )
    roots = set(_transform_facts(gltf).root_nodes)
    root_origins = tuple(
        (float(world[0, 3]), float(world[1, 3]), float(world[2, 3]))
        for node_index, world in iter_world_matrices(gltf)
        if node_index in roots
    )
    bounds = geometry.bounds
    ground_center = (
        (bounds.minimum_m[0] + bounds.maximum_m[0]) / 2.0,
        bounds.minimum_m[1],
        (bounds.minimum_m[2] + bounds.maximum_m[2]) / 2.0,
    )
    texture_dicts = cast(list[object], document.get("textures", []))
    return SourceDiagnostics(
        primitives=primitives,
        empty_leaf_node_indices=empty_leaf_nodes,
        unreachable_node_indices=tuple(sorted(set(range(len(gltf.nodes))) - reachable_nodes)),
        unused_mesh_indices=tuple(sorted(set(range(len(gltf.meshes))) - used_meshes)),
        unused_material_indices=tuple(sorted(set(range(len(gltf.materials))) - used_materials)),
        unused_texture_indices=tuple(sorted(set(range(len(gltf.textures))) - used_textures)),
        unused_image_indices=tuple(sorted(set(range(len(gltf.images))) - used_images)),
        unused_sampler_indices=tuple(sorted(set(range(len(gltf.samplers))) - used_samplers)),
        duplicate_material_groups=_duplicate_groups(material_dicts),
        duplicate_texture_groups=_duplicate_groups(texture_dicts),
        root_world_origins_m=root_origins,
        bounds_ground_center_m=ground_center,
    )


def _blocking_geometry_diagnostics(diagnostics: SourceDiagnostics) -> tuple[str, ...]:
    problems: list[str] = []
    for primitive in diagnostics.primitives:
        prefix = f"mesh:{primitive.mesh_index}/primitive:{primitive.primitive_index}"
        if primitive.attribute_count_mismatches:
            problems.extend(f"{prefix} {detail}" for detail in primitive.attribute_count_mismatches)
        counters = (
            ("non-finite positions", primitive.non_finite_position_count),
            ("non-finite normals", primitive.non_finite_normal_count),
            ("non-unit normals", primitive.non_unit_normal_count),
            ("non-finite tangents", primitive.non_finite_tangent_count),
            ("invalid tangent handedness", primitive.invalid_tangent_handedness_count),
            ("non-finite UVs", primitive.non_finite_texcoord_0_count),
            ("out-of-range indices", primitive.out_of_range_index_count),
        )
        problems.extend(f"{prefix} has {count} {label}" for label, count in counters if count)
    return tuple(problems)


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
    profile: ProjectProfile | None = None,
    policy: ProfilePolicyProvenance | None = None,
    basis: CheckBasis | None = None,
) -> Finding:
    return Finding(
        id=f"finding-{code.lower().replace('_', '-')}",
        code=code,
        domain=domain,
        title=title,
        description=description,
        severity=severity,
        action_class=action_class,
        basis=(
            basis
            if basis is not None
            else CheckBasis.FROZEN_PROJECT_POLICY
            if profile_rule is not None
            else CheckBasis.OBJECTIVE_SOURCE_DIAGNOSTIC
        ),
        confidence=confidence,
        affected_components=affected,
        evidence=evidence,
        profile_rule=profile_rule,
        rule_provenance=(
            finding_rule_provenance(profile, profile_rule, policy) if profile is not None else None
        ),
        candidate_repairs=candidates,
    )


def _naming_findings(
    naming: NamingFacts,
    profile: ProjectProfile,
    policy: ProfilePolicyProvenance | None,
) -> list[Finding]:
    findings: list[Finding] = []
    categories = (
        (
            "NODE_NAME_MISSING",
            naming.missing_node_indices,
            "Nodes are missing names",
            "node",
            "naming.pattern",
        ),
        (
            "NODE_NAME_INVALID",
            naming.invalid_node_indices,
            "Node names violate the project pattern",
            "node",
            "naming.pattern",
        ),
        (
            "NODE_NAME_DUPLICATE",
            (
                tuple(
                    index for indices in naming.duplicate_node_names.values() for index in indices
                )
                if profile.naming.require_unique_node_names
                else ()
            ),
            "Node names are not unique",
            "node",
            "naming.require_unique_node_names",
        ),
        (
            "MESH_NAME_MISSING",
            naming.missing_mesh_indices,
            "Meshes are missing names",
            "mesh",
            "naming.pattern",
        ),
        (
            "MESH_NAME_INVALID",
            naming.invalid_mesh_indices,
            "Mesh names violate the project pattern",
            "mesh",
            "naming.pattern",
        ),
        (
            "MESH_NAME_DUPLICATE",
            (
                tuple(
                    index for indices in naming.duplicate_mesh_names.values() for index in indices
                )
                if profile.naming.require_unique_mesh_names
                else ()
            ),
            "Mesh names are not unique",
            "mesh",
            "naming.require_unique_mesh_names",
        ),
    )
    for code, indices, title, component_type, profile_rule in categories:
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
                profile_rule=profile_rule,
                candidates=candidate_ids,
                profile=profile,
                policy=policy,
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
    diagnostics: SourceDiagnostics,
    policy: ProfilePolicyProvenance | None,
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
                basis=CheckBasis.UNIVERSAL_INVARIANT,
            )
        )

    malformed_geometry = _blocking_geometry_diagnostics(diagnostics)
    if malformed_geometry:
        eligibility = RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES
        findings.append(
            _finding(
                code="MALFORMED_GEOMETRY_ATTRIBUTES",
                domain="geometry",
                title="Geometry attributes violate universal validity rules",
                description=(
                    "The asset remains inspectable, but repair is blocked because attribute or "
                    "index integrity cannot be proven."
                ),
                severity=Severity.BLOCKER,
                action_class=ActionClass.BLOCKED,
                confidence=1.0,
                affected=tuple(
                    sorted({problem.partition(" ")[0] for problem in malformed_geometry})
                ),
                evidence=tuple(
                    FindingEvidence(observation=problem) for problem in malformed_geometry
                ),
                profile_rule=None,
                basis=CheckBasis.UNIVERSAL_INVARIANT,
            )
        )

    degenerate_primitives = tuple(
        primitive for primitive in diagnostics.primitives if primitive.degenerate_triangle_count
    )
    if degenerate_primitives:
        findings.append(
            _finding(
                code="DEGENERATE_TRIANGLES_DETECTED",
                domain="geometry",
                title="Degenerate triangle indices detected",
                description=(
                    "Degenerate triangles are objective source diagnostics; version 1 does not "
                    "alter topology."
                ),
                severity=Severity.WARNING,
                action_class=ActionClass.REPORT_ONLY,
                confidence=1.0,
                affected=tuple(
                    f"mesh:{item.mesh_index}/primitive:{item.primitive_index}"
                    for item in degenerate_primitives
                ),
                evidence=tuple(
                    FindingEvidence(
                        observation=(
                            f"Mesh {item.mesh_index} primitive {item.primitive_index} contains "
                            f"{item.degenerate_triangle_count} degenerate indexed triangles."
                        ),
                        observed_value=item.degenerate_triangle_count,
                    )
                    for item in degenerate_primitives
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
                profile=profile,
                policy=policy,
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
                profile=profile,
                policy=policy,
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
                profile=profile,
                policy=policy,
            )
        )

    findings.extend(_naming_findings(naming, profile, policy))
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
                profile=profile,
                policy=policy,
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
                profile=profile,
                policy=policy,
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
                profile=profile,
                policy=policy,
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
                description="Unreadable image data cannot be verified.",
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


def preflight_asset(path: Path) -> PreflightResult:
    """Measure profile-free source facts without findings, planning, or mutation."""
    try:
        source_bytes = path.read_bytes()
    except OSError as error:
        source_bytes = b""
        read_error: Exception | None = error
    else:
        read_error = None
    source_hash = sha256(source_bytes).hexdigest()
    preflight_id = f"preflight-{source_hash[:16]}-v1"
    try:
        if read_error is not None:
            raise GlbError(f"Could not read source file: {read_error}")
        gltf = load_glb(path)
        validate_loaded_glb(gltf)
        bounds = world_bounds(gltf)
        counts = geometry_counts(gltf)
        bounds_model = _bounds_model(bounds.minimum, bounds.maximum)
        dominant_axis = ("X", "Y", "Z")[int(np.argmax(bounds.dimensions))]
        minimum_y = float(bounds.minimum[1])
        epsilon = 1e-9
        if minimum_y < -epsilon:
            ground = "EXTENDS_BELOW"
        elif minimum_y > epsilon:
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
        diagnostics = _source_diagnostics(gltf, geometry)
        package = _package_facts(gltf, file_sha256=source_hash, byte_size=len(source_bytes))
        unsupported_structure = bool(
            package.skin_count
            or package.animation_count
            or package.has_morph_targets
            or (set(package.extensions_required) - SUPPORTED_REQUIRED_EXTENSIONS)
            or _blocking_geometry_diagnostics(diagnostics)
        )
        eligibility = (
            RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES
            if unsupported_structure
            else RepairEligibility.ELIGIBLE_STATIC_MESH
        )
        return PreflightResult(
            preflight_id=preflight_id,
            source_filename=path.name,
            package=package,
            geometry=geometry,
            transforms=_transform_facts(gltf),
            materials=_material_facts(gltf),
            structural_eligibility=eligibility,
            parse_error=None,
            diagnostics=diagnostics,
        )
    except (GlbError, OSError, ValueError, IndexError, TypeError) as error:
        return PreflightResult(
            preflight_id=preflight_id,
            source_filename=path.name,
            package=_empty_package_facts(source_hash, len(source_bytes)),
            geometry=None,
            transforms=None,
            materials=(),
            structural_eligibility=RepairEligibility.INVALID_OR_UNREADABLE,
            parse_error=str(error),
            diagnostics=None,
        )


def inspect_asset(
    path: Path,
    profile: ProjectProfile,
    *,
    policy: ProfilePolicyProvenance | None = None,
) -> InspectionResult:
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
        diagnostics = _source_diagnostics(gltf, geometry)
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
            diagnostics,
            policy,
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
            diagnostics=diagnostics,
        )
    except (GlbError, OSError, ValueError, IndexError, TypeError) as error:
        finding = _finding(
            code="INVALID_OR_UNREADABLE",
            domain="package",
            title="Asset is invalid or unreadable",
            description="Inspection could not parse and measure this file.",
            severity=Severity.BLOCKER,
            action_class=ActionClass.BLOCKED,
            confidence=1.0,
            affected=(path.name,),
            evidence=(FindingEvidence(observation=str(error)),),
            profile_rule=None,
            basis=CheckBasis.UNIVERSAL_INVARIANT,
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
            diagnostics=None,
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
    if inspection.diagnostics is not None:
        primitives = inspection.diagnostics.primitives
        lines.extend(
            (
                "",
                "## Objective diagnostics",
                "",
                f"- Primitive attributes: {sum(item.has_normals for item in primitives)}/"
                f"{len(primitives)} normals, {sum(item.has_tangents for item in primitives)}/"
                f"{len(primitives)} tangents, {sum(item.has_texcoord_0 for item in primitives)}/"
                f"{len(primitives)} primary UV sets",
                f"- Empty leaf nodes: {list(inspection.diagnostics.empty_leaf_node_indices)}",
                f"- Unused resources: {len(inspection.diagnostics.unused_mesh_indices)} meshes, "
                f"{len(inspection.diagnostics.unused_material_indices)} materials, "
                f"{len(inspection.diagnostics.unused_texture_indices)} textures, "
                f"{len(inspection.diagnostics.unused_image_indices)} images",
                "- Apparent duplicate records: "
                f"{len(inspection.diagnostics.duplicate_material_groups)} material groups, "
                f"{len(inspection.diagnostics.duplicate_texture_groups)} texture groups",
            )
        )
    lines.extend(("", "## Findings", ""))
    if not inspection.findings:
        lines.append("No project-policy findings.")
    else:
        lines.extend(
            (
                "| Severity | Code | Finding | Basis | Action |",
                "|---|---|---|---|---|",
            )
        )
        lines.extend(
            f"| {finding.severity} | `{finding.code}` | {finding.title} | {finding.basis} | "
            f"{finding.action_class} |"
            for finding in inspection.findings
        )
    return "\n".join(lines) + "\n"
