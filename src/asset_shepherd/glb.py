"""Low-level GLB access used by the deterministic asset core."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
import warnings
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
from pygltflib import (
    FLOAT,
    GLTF2,
    TRIANGLE_FAN,
    TRIANGLE_STRIP,
    TRIANGLES,
    Accessor,
    BufferView,
    Node,
)
from pygltflib.validator import validate as validate_gltf

FloatArray = npt.NDArray[np.float64]
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963


class GlbError(ValueError):
    """Raised when a GLB cannot be handled safely."""


@dataclass(frozen=True)
class Bounds:
    """World-space axis-aligned bounds in meters."""

    minimum: FloatArray
    maximum: FloatArray

    @property
    def dimensions(self) -> FloatArray:
        """Return the axis lengths in meters."""
        return self.maximum - self.minimum


@dataclass(frozen=True)
class GeometryCounts:
    """Structural geometry counts."""

    vertices: int
    triangles: int


def load_glb(path: Path) -> GLTF2:
    """Load a glTF 2.0 binary file after checking its container header."""
    header = path.read_bytes()[:12]
    if path.suffix.lower() != ".glb":
        msg = f"Expected a .glb file, received {path.suffix or 'no extension'}"
        raise GlbError(msg)
    if len(header) != 12 or header[:4] != b"glTF":
        raise GlbError("File does not have a valid GLB header")
    version = int.from_bytes(header[4:8], byteorder="little")
    if version != 2:
        msg = f"Only glTF 2.0 is supported, received GLB version {version}"
        raise GlbError(msg)
    loaded = GLTF2().load_binary(str(path))
    if loaded is None:
        raise GlbError("pygltflib could not load the GLB")
    return loaded


def raw_glb_document(path: Path) -> dict[str, object]:
    """Decode the container JSON chunk without dropping unknown attribute semantics."""
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"glTF":
        raise GlbError("File does not have a readable GLB JSON chunk")
    json_length = int.from_bytes(payload[12:16], byteorder="little")
    json_type = int.from_bytes(payload[16:20], byteorder="little")
    if json_type != 0x4E4F534A or 20 + json_length > len(payload):
        raise GlbError("GLB does not begin with a valid JSON chunk")
    try:
        document = json.loads(payload[20 : 20 + json_length].rstrip(b"\x00 ").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GlbError("GLB JSON chunk is unreadable") from error
    if not isinstance(document, dict):
        raise GlbError("GLB JSON document is not an object")
    return cast(dict[str, object], document)


def save_glb(gltf: GLTF2, path: Path) -> None:
    """Save a GLB without mutating the source path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not gltf.save_binary(str(path)):
        raise GlbError("pygltflib could not save the GLB")


def validate_loaded_glb(gltf: GLTF2) -> None:
    """Run pygltflib's provisional structural validation checks."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        errors = cast(list[Exception], validate_gltf(gltf, warning=True))
    if errors:
        detail = "; ".join(str(error) for error in errors)
        raise GlbError(f"glTF structural validation failed: {detail}")


def geometry_counts(gltf: GLTF2) -> GeometryCounts:
    """Count vertices and triangle-list faces without expanding scene instances."""
    vertices = 0
    triangles = 0
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            position_index = cast(object, primitive.attributes.POSITION)
            if not isinstance(position_index, int):
                raise GlbError("Mesh primitive has no POSITION accessor")
            position_accessor = gltf.accessors[position_index]
            vertices += position_accessor.count
            element_count = (
                position_accessor.count
                if primitive.indices is None
                else gltf.accessors[primitive.indices].count
            )
            if primitive.mode == TRIANGLES:
                triangles += element_count // 3
            elif primitive.mode in {TRIANGLE_STRIP, TRIANGLE_FAN}:
                triangles += max(element_count - 2, 0)
    return GeometryCounts(vertices=vertices, triangles=triangles)


def accessor_array(gltf: GLTF2, accessor_index: int) -> npt.NDArray[np.generic]:
    """Decode a dense accessor from the embedded GLB binary chunk."""
    accessor = gltf.accessors[accessor_index]
    if accessor.sparse is not None:
        raise GlbError("Sparse accessors are not supported by the capability spike")
    if accessor.bufferView is None:
        raise GlbError("Accessor has no buffer view")
    view = gltf.bufferViews[accessor.bufferView]
    if view.buffer != 0:
        raise GlbError("GLB accessor references a non-primary buffer")

    component_types: dict[int, npt.DTypeLike] = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        FLOAT: np.float32,
    }
    component_counts = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    try:
        dtype = np.dtype(component_types[accessor.componentType])
        component_count = component_counts[accessor.type]
    except KeyError as error:
        raise GlbError("Accessor uses an unsupported component or shape") from error

    blob = cast(bytes | bytearray | None, gltf.binary_blob())
    if blob is None:
        raise GlbError("GLB has no binary chunk")
    offset = (view.byteOffset or 0) + (accessor.byteOffset or 0)
    packed_stride = dtype.itemsize * component_count
    stride = view.byteStride or packed_stride
    final_byte = offset + max(accessor.count - 1, 0) * stride + packed_stride
    if offset < 0 or final_byte > len(blob):
        raise GlbError("Accessor exceeds the embedded binary chunk")

    return np.ndarray(
        shape=(accessor.count, component_count),
        dtype=dtype,
        buffer=blob,
        offset=offset,
        strides=(stride, dtype.itemsize),
    ).copy()


def node_local_matrix(node: Node) -> FloatArray:
    """Return a node's glTF column-vector local transform."""
    if node.matrix:
        return np.asarray(node.matrix, dtype=np.float64).reshape((4, 4)).T

    translation = np.asarray(node.translation or [0.0, 0.0, 0.0], dtype=np.float64)
    scale = np.asarray(node.scale or [1.0, 1.0, 1.0], dtype=np.float64)
    quaternion = np.asarray(node.rotation or [0.0, 0.0, 0.0, 1.0], dtype=np.float64)
    quaternion_norm = np.linalg.norm(quaternion)
    if quaternion_norm == 0:
        raise GlbError("Node rotation quaternion has zero length")
    x, y, z, w = quaternion / quaternion_norm
    rotation = np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
    local = np.eye(4, dtype=np.float64)
    local[:3, :3] = rotation @ np.diag(scale)
    local[:3, 3] = translation
    return local


def iter_world_matrices(gltf: GLTF2) -> Iterator[tuple[int, FloatArray]]:
    """Yield active-scene nodes and their world transforms in depth-first order."""
    if not gltf.scenes:
        raise GlbError("GLB has no scenes")
    configured_scene = cast(int | None, gltf.scene)
    scene_index = configured_scene if configured_scene is not None else 0
    if not 0 <= scene_index < len(gltf.scenes):
        raise GlbError("Active scene index is invalid")
    roots = gltf.scenes[scene_index].nodes or []

    def walk(
        node_index: int,
        parent: FloatArray,
        ancestors: frozenset[int],
    ) -> Iterator[tuple[int, FloatArray]]:
        if node_index in ancestors:
            raise GlbError("Node hierarchy contains a cycle")
        if not 0 <= node_index < len(gltf.nodes):
            raise GlbError("Scene references an invalid node")
        node = gltf.nodes[node_index]
        world = parent @ node_local_matrix(node)
        yield node_index, world
        next_ancestors = ancestors | {node_index}
        for child_index in node.children or []:
            yield from walk(child_index, world, next_ancestors)

    identity = np.eye(4, dtype=np.float64)
    for root_index in roots:
        yield from walk(root_index, identity, frozenset())


def world_bounds(gltf: GLTF2) -> Bounds:
    """Compute active-scene bounds from positions referenced by surviving primitives."""
    minimum = np.full(3, np.inf, dtype=np.float64)
    maximum = np.full(3, -np.inf, dtype=np.float64)
    found_positions = False
    for node_index, world in iter_world_matrices(gltf):
        mesh_index = gltf.nodes[node_index].mesh
        if mesh_index is None:
            continue
        if not 0 <= mesh_index < len(gltf.meshes):
            raise GlbError("Node references an invalid mesh")
        for primitive in gltf.meshes[mesh_index].primitives:
            position_index = cast(object, primitive.attributes.POSITION)
            if not isinstance(position_index, int):
                raise GlbError("Mesh primitive has no POSITION accessor")
            positions = accessor_array(gltf, position_index).astype(np.float64)
            indices_index = cast(object, primitive.indices)
            if indices_index is not None:
                if not isinstance(indices_index, int):
                    raise GlbError("Mesh primitive has an invalid index accessor")
                indices = cast(
                    npt.NDArray[np.int64],
                    np.asarray(accessor_array(gltf, indices_index), dtype=np.int64).reshape(-1),
                )
                if len(indices) == 0:
                    continue
                if np.any(indices < 0) or np.any(indices >= len(positions)):
                    raise GlbError("Mesh primitive contains an out-of-range vertex index")
                positions = positions[indices]
            if len(positions) == 0:
                continue
            homogeneous = np.column_stack((positions, np.ones(len(positions), dtype=np.float64)))
            transformed = (world @ homogeneous.T).T[:, :3]
            minimum = np.minimum(minimum, transformed.min(axis=0))
            maximum = np.maximum(maximum, transformed.max(axis=0))
            found_positions = True
    if not found_positions:
        raise GlbError("Active scene contains no mesh positions")
    return Bounds(minimum=minimum, maximum=maximum)


def add_normalization_root(gltf: GLTF2, matrix: FloatArray, *, name: str) -> int:
    """Parent the active scene roots beneath a reversible normalization node."""
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise GlbError("Normalization transform must be a finite 4x4 matrix")
    if not gltf.scenes:
        raise GlbError("GLB has no scenes")
    configured_scene = cast(int | None, gltf.scene)
    scene_index = configured_scene if configured_scene is not None else 0
    scene = gltf.scenes[scene_index]
    roots = list(scene.nodes or [])
    root_index = len(gltf.nodes)
    gltf.nodes.append(Node(name=name, children=roots, matrix=matrix.T.reshape(-1).tolist()))
    scene.nodes = [root_index]
    return root_index


def _append_packed_accessor(
    gltf: GLTF2,
    blob: bytearray,
    values: npt.NDArray[np.generic],
    template: Accessor,
    *,
    target: int,
) -> int:
    """Append one tightly packed accessor without rewriting existing binary content."""
    while len(blob) % 4:
        blob.append(0)
    packed = np.ascontiguousarray(values).tobytes(order="C")
    view_index = len(gltf.bufferViews)
    gltf.bufferViews.append(
        BufferView(
            buffer=0,
            byteOffset=len(blob),
            byteLength=len(packed),
            target=target,
        )
    )
    blob.extend(packed)
    accessor = deepcopy(template)
    accessor.bufferView = view_index
    accessor.byteOffset = 0
    accessor.count = len(values)
    accessor.sparse = None
    accessor_index = len(gltf.accessors)
    gltf.accessors.append(accessor)
    return accessor_index


def degenerate_triangle_mask(
    positions: npt.NDArray[np.generic],
    triangles: npt.NDArray[np.int64],
) -> npt.NDArray[np.bool_]:
    """Identify repeated-index and scale-relative zero-area triangles deterministically."""
    triangle_indices = np.asarray(triangles, dtype=np.int64).reshape((-1, 3))
    repeated = (
        (triangle_indices[:, 0] == triangle_indices[:, 1])
        | (triangle_indices[:, 1] == triangle_indices[:, 2])
        | (triangle_indices[:, 0] == triangle_indices[:, 2])
    )
    degenerate = repeated.copy()
    valid = ~np.any(
        (triangle_indices < 0) | (triangle_indices >= len(positions)),
        axis=1,
    )
    candidates = valid & ~repeated
    if not np.any(candidates):
        return degenerate
    triangle_positions = np.asarray(positions)[triangle_indices[candidates], :3].astype(
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
    source_positions = np.asarray(positions)[:, :3]
    finite_source = source_positions[np.isfinite(source_positions).all(axis=1)].astype(
        np.float64,
        copy=False,
    )
    scale_squared = (
        max(float(np.dot(np.ptp(finite_source, axis=0), np.ptp(finite_source, axis=0))), 1.0)
        if len(finite_source)
        else 1.0
    )
    area_tolerance = np.finfo(np.float64).eps * scale_squared * 64.0
    degenerate[np.flatnonzero(candidates)] = twice_area <= area_tolerance
    return degenerate


def _refresh_accessor_bounds(accessor: Accessor, values: npt.NDArray[np.generic]) -> None:
    """Recompute declared accessor bounds after exact row compaction."""
    if not len(values):
        accessor.min = None
        accessor.max = None
        return
    numeric_values = cast(npt.NDArray[np.float64], np.asarray(values))
    if accessor.min is not None:
        accessor.min = np.min(numeric_values, axis=0).tolist()
    if accessor.max is not None:
        accessor.max = np.max(numeric_values, axis=0).tolist()


def clean_degenerate_geometry(
    gltf: GLTF2,
    expected_removals: dict[tuple[int, int], tuple[int, int]],
) -> dict[tuple[int, int], tuple[int, int]]:
    """Remove proven zero-area triangles and compact only their unreferenced vertex tuples.

    Every surviving corner keeps the same complete attribute tuple and order. Existing binary data
    remains an immutable prefix; repaired accessors and indices are appended to the GLB.
    """
    original_blob = cast(bytes | bytearray | None, gltf.binary_blob())
    if original_blob is None or not gltf.buffers:
        raise GlbError("GLB has no primary binary buffer")
    blob = bytearray(original_blob)
    actual: dict[tuple[int, int], tuple[int, int]] = {}
    for (mesh_index, primitive_index), expected in sorted(expected_removals.items()):
        if not 0 <= mesh_index < len(gltf.meshes):
            raise GlbError("Geometry cleanup references an invalid mesh")
        mesh = gltf.meshes[mesh_index]
        if not 0 <= primitive_index < len(mesh.primitives):
            raise GlbError("Geometry cleanup references an invalid primitive")
        primitive = mesh.primitives[primitive_index]
        mode = primitive.mode if primitive.mode is not None else TRIANGLES
        if mode != TRIANGLES or primitive.indices is None:
            raise GlbError("Geometry cleanup requires an indexed TRIANGLES primitive")
        if primitive.targets or primitive.extensions:
            raise GlbError(
                "Geometry cleanup does not support morph targets or compressed primitives"
            )

        attribute_indices = {
            semantic: accessor_index
            for semantic, accessor_index in vars(primitive.attributes).items()
            if isinstance(accessor_index, int)
        }
        position_index = attribute_indices.get("POSITION")
        if position_index is None:
            raise GlbError("Geometry cleanup primitive has no POSITION accessor")
        arrays = {
            semantic: accessor_array(gltf, accessor_index)
            for semantic, accessor_index in attribute_indices.items()
        }
        position_count = len(arrays["POSITION"])
        if any(len(values) != position_count for values in arrays.values()):
            raise GlbError("Geometry cleanup requires matching attribute cardinalities")
        for accessor_index in (*attribute_indices.values(), primitive.indices):
            accessor = gltf.accessors[accessor_index]
            view = gltf.bufferViews[cast(int, accessor.bufferView)]
            if accessor.sparse is not None or accessor.extensions or view.extensions:
                raise GlbError("Geometry cleanup requires dense, unextended accessors")

        old_indices = np.asarray(
            accessor_array(gltf, primitive.indices),
            dtype=np.int64,
        ).reshape(-1)
        if len(old_indices) % 3:
            raise GlbError("Geometry cleanup requires complete triangle index triples")
        triangles = old_indices.reshape((-1, 3))
        invalid = (triangles < 0) | (triangles >= position_count)
        if np.any(invalid):
            raise GlbError("Geometry cleanup refuses out-of-range indices")
        degenerate = degenerate_triangle_mask(arrays["POSITION"], triangles)
        surviving = triangles[~degenerate]
        if not len(surviving):
            raise GlbError("Geometry cleanup refuses to remove every triangle")
        used = np.unique(surviving.reshape(-1))
        if not len(used):
            raise GlbError("Geometry cleanup produced no referenced vertices")
        removed_triangles = int(np.count_nonzero(degenerate))
        removed_positions = position_count - len(used)
        if (removed_triangles, removed_positions) != expected:
            raise GlbError(
                "Geometry cleanup evidence changed since planning: "
                f"expected {expected}, measured {(removed_triangles, removed_positions)}"
            )
        if not (removed_triangles or removed_positions):
            raise GlbError("Geometry cleanup selected a primitive with no removable data")

        old_to_new = np.full(position_count, -1, dtype=np.int64)
        old_to_new[used] = np.arange(len(used), dtype=np.int64)
        for semantic, old_accessor_index in sorted(attribute_indices.items()):
            compacted = arrays[semantic][used]
            new_accessor_index = _append_packed_accessor(
                gltf,
                blob,
                compacted,
                gltf.accessors[old_accessor_index],
                target=ARRAY_BUFFER,
            )
            _refresh_accessor_bounds(gltf.accessors[new_accessor_index], compacted)
            setattr(primitive.attributes, semantic, new_accessor_index)

        remapped = old_to_new[surviving].reshape(-1)
        if len(used) <= 255:
            packed_indices = remapped.astype(np.uint8, copy=False).reshape((-1, 1))
            component_type = 5121
        elif len(used) <= 65535:
            packed_indices = remapped.astype(np.uint16, copy=False).reshape((-1, 1))
            component_type = 5123
        else:
            packed_indices = remapped.astype(np.uint32, copy=False).reshape((-1, 1))
            component_type = 5125
        index_template = Accessor(
            componentType=component_type,
            count=len(packed_indices),
            type="SCALAR",
            max=[int(remapped.max())],
            min=[int(remapped.min())],
        )
        primitive.indices = _append_packed_accessor(
            gltf,
            blob,
            packed_indices,
            index_template,
            target=ELEMENT_ARRAY_BUFFER,
        )
        actual[(mesh_index, primitive_index)] = (removed_triangles, removed_positions)

    gltf.set_binary_blob(bytes(blob))
    gltf.buffers[0].byteLength = len(blob)
    return actual


def remove_disconnected_components(
    gltf: GLTF2,
    expected_selections: dict[tuple[int, int], tuple[tuple[str, ...], int]],
) -> dict[tuple[int, int], int]:
    """Remove only exact position-projected components frozen in an approved plan.

    Vertex attributes are not rewritten. The replacement index accessor is append-only, and any
    newly unreferenced complete vertex tuples remain visible to the next inspection turn.
    """
    from asset_shepherd.mesh_diagnostics import enumerate_connected_components

    original_blob = cast(bytes | bytearray | None, gltf.binary_blob())
    if original_blob is None or not gltf.buffers:
        raise GlbError("GLB has no primary binary buffer")
    blob = bytearray(original_blob)
    actual: dict[tuple[int, int], int] = {}
    for (mesh_index, primitive_index), (approved_ids, expected_removed) in sorted(
        expected_selections.items()
    ):
        if not 0 <= mesh_index < len(gltf.meshes):
            raise GlbError("Component removal references an invalid mesh")
        mesh = gltf.meshes[mesh_index]
        if not 0 <= primitive_index < len(mesh.primitives):
            raise GlbError("Component removal references an invalid primitive")
        primitive = mesh.primitives[primitive_index]
        mode = primitive.mode if primitive.mode is not None else TRIANGLES
        if mode != TRIANGLES or primitive.indices is None:
            raise GlbError("Component removal requires an indexed TRIANGLES primitive")
        if primitive.targets or primitive.extensions:
            raise GlbError("Component removal does not support morph or compressed primitives")
        if sum(node.mesh == mesh_index for node in gltf.nodes) != 1:
            raise GlbError("Component removal requires exactly one mesh instance")
        if any(node.mesh == mesh_index and node.skin is not None for node in gltf.nodes):
            raise GlbError("Component removal refuses skinned mesh instances")

        attribute_indices = {
            semantic: accessor_index
            for semantic, accessor_index in vars(primitive.attributes).items()
            if isinstance(accessor_index, int)
        }
        position_index = attribute_indices.get("POSITION")
        if position_index is None:
            raise GlbError("Component removal primitive has no POSITION accessor")
        arrays = {
            semantic: accessor_array(gltf, accessor_index)
            for semantic, accessor_index in attribute_indices.items()
        }
        position_count = len(arrays["POSITION"])
        if any(len(values) != position_count for values in arrays.values()):
            raise GlbError("Component removal requires matching attribute cardinalities")
        for accessor_index in (*attribute_indices.values(), primitive.indices):
            accessor = gltf.accessors[accessor_index]
            if accessor.bufferView is None:
                raise GlbError("Component removal requires dense accessors")
            view = gltf.bufferViews[accessor.bufferView]
            if (
                accessor.sparse is not None
                or accessor.extensions
                or view.extensions
                or view.buffer != 0
            ):
                raise GlbError("Component removal requires dense, unextended primary-buffer data")

        old_indices = np.asarray(accessor_array(gltf, primitive.indices), dtype=np.int64).reshape(
            -1
        )
        if len(old_indices) % 3:
            raise GlbError("Component removal requires complete triangle index triples")
        triangles = old_indices.reshape((-1, 3))
        if np.any((triangles < 0) | (triangles >= position_count)):
            raise GlbError("Component removal refuses out-of-range indices")
        if np.any(degenerate_triangle_mask(arrays["POSITION"], triangles)):
            raise GlbError("Component removal requires degenerate cleanup in a separate turn")
        inventory = enumerate_connected_components(
            arrays["POSITION"],
            triangles,
            mesh_index=mesh_index,
            primitive_index=primitive_index,
        )
        if inventory.truncated:
            raise GlbError("Component removal refuses a truncated component inventory")
        by_id = {component.component_id: component for component in inventory.components}
        requested = set(approved_ids)
        unknown = requested - set(by_id)
        if unknown:
            raise GlbError(f"Component identity changed since approval: {sorted(unknown)}")
        if requested == set(by_id):
            raise GlbError("Component removal refuses to remove every component")
        remove_faces = {
            face for component_id in approved_ids for face in by_id[component_id].face_indices
        }
        if len(remove_faces) != expected_removed:
            raise GlbError(
                "Component-removal evidence changed since planning: "
                f"expected {expected_removed}, measured {len(remove_faces)}"
            )
        keep_mask = np.ones(len(triangles), dtype=bool)
        keep_mask[list(remove_faces)] = False
        retained = triangles[keep_mask].reshape(-1)
        if not len(retained):
            raise GlbError("Component removal produced no retained triangles")
        if position_count <= 255:
            packed_indices = retained.astype(np.uint8, copy=False).reshape((-1, 1))
            component_type = 5121
        elif position_count <= 65535:
            packed_indices = retained.astype(np.uint16, copy=False).reshape((-1, 1))
            component_type = 5123
        else:
            packed_indices = retained.astype(np.uint32, copy=False).reshape((-1, 1))
            component_type = 5125
        index_template = Accessor(
            componentType=component_type,
            count=len(packed_indices),
            type="SCALAR",
            max=[int(retained.max())],
            min=[int(retained.min())],
        )
        primitive.indices = _append_packed_accessor(
            gltf,
            blob,
            packed_indices,
            index_template,
            target=ELEMENT_ARRAY_BUFFER,
        )
        actual[(mesh_index, primitive_index)] = len(remove_faces)

    gltf.set_binary_blob(bytes(blob))
    gltf.buffers[0].byteLength = len(blob)
    return actual


def weld_identical_vertex_tuples(
    gltf: GLTF2,
    expected_merges: dict[tuple[int, int], int],
) -> dict[tuple[int, int], int]:
    """Compact byte-identical complete vertex tuples for selected primitives.

    POSITION alone never determines mergeability. Every standard attribute on the primitive must
    be present, dense, cardinality-matched, and byte-identical before two indices can be joined.
    """
    from asset_shepherd.mesh_diagnostics import attribute_safe_weld_mapping

    original_blob = cast(bytes | bytearray | None, gltf.binary_blob())
    if original_blob is None or not gltf.buffers:
        raise GlbError("GLB has no primary binary buffer")
    blob = bytearray(original_blob)
    actual_merges: dict[tuple[int, int], int] = {}
    for (mesh_index, primitive_index), expected_merge_count in sorted(expected_merges.items()):
        if not 0 <= mesh_index < len(gltf.meshes):
            raise GlbError("Weld references an invalid mesh")
        mesh = gltf.meshes[mesh_index]
        if not 0 <= primitive_index < len(mesh.primitives):
            raise GlbError("Weld references an invalid primitive")
        primitive = mesh.primitives[primitive_index]
        if primitive.targets or primitive.extensions:
            raise GlbError("Weld does not support morph targets or compressed primitives")

        attribute_indices = {
            semantic: accessor_index
            for semantic, accessor_index in vars(primitive.attributes).items()
            if isinstance(accessor_index, int)
        }
        position_index = attribute_indices.get("POSITION")
        if position_index is None:
            raise GlbError("Weld primitive has no POSITION accessor")
        arrays = {
            semantic: accessor_array(gltf, accessor_index)
            for semantic, accessor_index in attribute_indices.items()
        }
        position_count = len(arrays["POSITION"])
        if any(len(values) != position_count for values in arrays.values()):
            raise GlbError("Weld requires matching attribute cardinalities")
        for accessor_index in attribute_indices.values():
            accessor = gltf.accessors[accessor_index]
            view = gltf.bufferViews[cast(int, accessor.bufferView)]
            if accessor.sparse is not None or accessor.extensions or view.extensions:
                raise GlbError("Weld requires dense, unextended vertex accessors")

        protected = {key: value for key, value in arrays.items() if key != "POSITION"}
        inverse, representatives = attribute_safe_weld_mapping(arrays["POSITION"], protected)
        merge_count = position_count - len(representatives)
        if merge_count != expected_merge_count:
            raise GlbError(
                "Weld evidence changed since planning: "
                f"expected {expected_merge_count}, measured {merge_count}"
            )
        if merge_count <= 0:
            raise GlbError("Weld selected a primitive with no attribute-safe duplicate tuples")

        for semantic, old_accessor_index in sorted(attribute_indices.items()):
            compacted = arrays[semantic][representatives]
            new_accessor_index = _append_packed_accessor(
                gltf,
                blob,
                compacted,
                gltf.accessors[old_accessor_index],
                target=ARRAY_BUFFER,
            )
            setattr(primitive.attributes, semantic, new_accessor_index)

        if primitive.indices is None:
            old_indices = np.arange(position_count, dtype=np.int64)
        else:
            old_indices = np.asarray(
                accessor_array(gltf, primitive.indices),
                dtype=np.int64,
            ).reshape(-1)
        remapped = inverse[old_indices]
        packed_indices: npt.NDArray[np.uint16] | npt.NDArray[np.uint32]
        if len(representatives) <= 65535:
            packed_indices = remapped.astype(np.uint16, copy=False).reshape((-1, 1))
            component_type = 5123
        else:
            packed_indices = remapped.astype(np.uint32, copy=False).reshape((-1, 1))
            component_type = 5125
        index_template = Accessor(
            componentType=component_type,
            count=len(packed_indices),
            type="SCALAR",
            max=[int(remapped.max(initial=0))],
            min=[int(remapped.min(initial=0))],
        )
        primitive.indices = _append_packed_accessor(
            gltf,
            blob,
            packed_indices,
            index_template,
            target=ELEMENT_ARRAY_BUFFER,
        )
        actual_merges[(mesh_index, primitive_index)] = merge_count

    gltf.set_binary_blob(bytes(blob))
    gltf.buffers[0].byteLength = len(blob)
    return actual_merges
