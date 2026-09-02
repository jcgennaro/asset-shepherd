"""Low-level GLB access used by the deterministic asset core."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import ctypes
import json
import warnings
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import meshoptimizer
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


@dataclass(frozen=True)
class PrimitiveSimplificationResult:
    """Measured result of one deterministic primitive simplification."""

    before_triangles: int
    after_triangles: int
    before_positions: int
    after_positions: int
    protected_components: int
    result_error: float


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


def _normalized_attribute_values(
    values: npt.NDArray[np.generic],
    accessor: Accessor,
) -> npt.NDArray[np.float32]:
    """Convert one accessor to finite float values used only by the error metric."""
    result = np.asarray(values, dtype=np.float32)
    if accessor.normalized and np.issubdtype(values.dtype, np.integer):
        info = np.iinfo(cast(npt.DTypeLike, values.dtype))
        if np.issubdtype(values.dtype, np.signedinteger):
            result = np.maximum(result / float(info.max), -1.0)
        else:
            result = result / float(info.max)
    return np.ascontiguousarray(result)


def _simplification_attribute_metric(
    arrays: dict[str, npt.NDArray[np.generic]],
    accessors: dict[str, Accessor],
    used: npt.NDArray[np.int64],
) -> tuple[npt.NDArray[np.float32] | None, npt.NDArray[np.float32] | None]:
    """Build a bounded normal/UV/color metric without changing stored attributes."""
    parts: list[npt.NDArray[np.float32]] = []
    weights: list[float] = []
    semantic_weights = {
        "NORMAL": 0.5,
        "TANGENT": 0.25,
        "TEXCOORD_0": 0.2,
        "TEXCOORD_1": 0.1,
        "COLOR_0": 0.5,
    }
    for semantic, weight in semantic_weights.items():
        values = arrays.get(semantic)
        accessor = accessors.get(semantic)
        if values is None or accessor is None:
            continue
        metric = _normalized_attribute_values(values[used], accessor)
        if semantic == "TANGENT" and metric.shape[1] == 4:
            metric = metric[:, :3]
        if not np.isfinite(metric).all() or len(weights) + metric.shape[1] > 16:
            continue
        parts.append(metric)
        weights.extend([weight] * metric.shape[1])
    if not parts:
        return None, None
    return (
        np.ascontiguousarray(np.column_stack(parts), dtype=np.float32),
        np.asarray(weights, dtype=np.float32),
    )


def _allocated_component_targets(
    triangle_counts: list[int],
    target_total: int,
) -> list[int]:
    """Distribute one primitive target deterministically across reducible components."""
    if not triangle_counts:
        return []
    minimum_total = len(triangle_counts)
    available = max(minimum_total, target_total)
    total = sum(triangle_counts)
    exact = [available * count / total for count in triangle_counts]
    targets = [
        max(1, min(count - 1, int(value)))
        for count, value in zip(triangle_counts, exact, strict=True)
    ]
    remaining = available - sum(targets)
    order = sorted(
        range(len(targets)),
        key=lambda index: (exact[index] - int(exact[index]), triangle_counts[index], -index),
        reverse=True,
    )
    while remaining > 0:
        changed = False
        for index in order:
            if targets[index] < triangle_counts[index] - 1:
                targets[index] += 1
                remaining -= 1
                changed = True
                if remaining == 0:
                    break
        if not changed:
            break
    return targets


def _compact_primary_buffer(
    gltf: GLTF2,
    original_blob: bytes | bytearray,
    replacements: dict[int, bytes],
) -> None:
    """Rewrite existing buffer-view slots tightly while preserving their identities."""
    compacted = bytearray()
    for view_index, view in enumerate(gltf.bufferViews):
        if view.buffer != 0:
            raise GlbError("Mesh simplification supports one embedded primary buffer")
        while len(compacted) % 4:
            compacted.append(0)
        old_offset = view.byteOffset or 0
        payload = replacements.get(view_index)
        if payload is None:
            end = old_offset + view.byteLength
            if old_offset < 0 or end > len(original_blob):
                raise GlbError("A preserved buffer view exceeds the embedded binary payload")
            payload = bytes(original_blob[old_offset:end])
        view.byteOffset = len(compacted)
        view.byteLength = len(payload)
        compacted.extend(payload)
    gltf.set_binary_blob(bytes(compacted))
    gltf.buffers[0].byteLength = len(compacted)


def simplify_mesh_primitives(
    gltf: GLTF2,
    requests: dict[tuple[int, int], tuple[int, int, float, float]],
) -> dict[tuple[int, int], PrimitiveSimplificationResult]:
    """Reduce approved indexed triangle primitives without synthesizing vertex attributes.

    The replacement indices select only original complete vertex tuples. Exact disconnected
    components below the protection threshold are copied unchanged. The routine refuses shared,
    sparse, interleaved, morphed, skinned, or compressed layouts rather than broadening authority.
    """
    from asset_shepherd.mesh_diagnostics import enumerate_connected_components

    original_blob = cast(bytes | bytearray | None, gltf.binary_blob())
    if original_blob is None or not gltf.buffers:
        raise GlbError("GLB has no primary binary buffer")
    accessor_view_counts: dict[int, int] = {}
    for accessor in gltf.accessors:
        if accessor.bufferView is not None:
            accessor_view_counts[accessor.bufferView] = (
                accessor_view_counts.get(accessor.bufferView, 0) + 1
            )
    replacements: dict[int, bytes] = {}
    results: dict[tuple[int, int], PrimitiveSimplificationResult] = {}
    for (mesh_index, primitive_index), (
        target_triangles,
        protected_threshold,
        target_error,
        max_bounds_drift,
    ) in sorted(requests.items()):
        if not 0 <= mesh_index < len(gltf.meshes):
            raise GlbError("Mesh simplification references an invalid mesh")
        mesh = gltf.meshes[mesh_index]
        if not 0 <= primitive_index < len(mesh.primitives):
            raise GlbError("Mesh simplification references an invalid primitive")
        primitive = mesh.primitives[primitive_index]
        mode = primitive.mode if primitive.mode is not None else TRIANGLES
        if mode != TRIANGLES or primitive.indices is None:
            raise GlbError("Mesh simplification requires an indexed TRIANGLES primitive")
        if primitive.targets or primitive.extensions:
            raise GlbError("Mesh simplification refuses morph or compressed primitives")
        if any(node.mesh == mesh_index and node.skin is not None for node in gltf.nodes):
            raise GlbError("Mesh simplification refuses skinned mesh instances")

        attribute_indices = {
            semantic: accessor_index
            for semantic, accessor_index in vars(primitive.attributes).items()
            if isinstance(accessor_index, int)
        }
        if "POSITION" not in attribute_indices:
            raise GlbError("Mesh simplification primitive has no POSITION accessor")
        selected_accessor_indices = (*attribute_indices.values(), primitive.indices)
        for accessor_index in selected_accessor_indices:
            accessor = gltf.accessors[accessor_index]
            if accessor.bufferView is None:
                raise GlbError("Mesh simplification requires dense accessors")
            view = gltf.bufferViews[accessor.bufferView]
            packed_components = {
                "SCALAR": 1,
                "VEC2": 2,
                "VEC3": 3,
                "VEC4": 4,
            }.get(accessor.type)
            component_bytes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}.get(
                accessor.componentType
            )
            if (
                accessor.sparse is not None
                or accessor.extensions
                or view.extensions
                or view.buffer != 0
                or accessor.byteOffset not in {None, 0}
                or view.byteStride not in {None, 0}
                or accessor_view_counts.get(accessor.bufferView) != 1
                or packed_components is None
                or component_bytes is None
                or view.byteLength != accessor.count * packed_components * component_bytes
            ):
                raise GlbError(
                    "Mesh simplification requires dedicated, tightly packed, unextended accessors"
                )
        arrays = {
            semantic: accessor_array(gltf, accessor_index)
            for semantic, accessor_index in attribute_indices.items()
        }
        position_count = len(arrays["POSITION"])
        if any(len(values) != position_count for values in arrays.values()):
            raise GlbError("Mesh simplification requires matching attribute cardinalities")
        old_indices = np.asarray(accessor_array(gltf, primitive.indices), dtype=np.int64).reshape(
            -1
        )
        if len(old_indices) % 3:
            raise GlbError("Mesh simplification requires complete triangle triples")
        triangles = old_indices.reshape((-1, 3))
        if target_triangles <= 0 or target_triangles >= len(triangles):
            raise GlbError("Mesh simplification target is not a reduction")
        if np.any((triangles < 0) | (triangles >= position_count)):
            raise GlbError("Mesh simplification refuses out-of-range indices")
        if np.any(degenerate_triangle_mask(arrays["POSITION"], triangles)):
            raise GlbError("Mesh simplification requires degenerate cleanup in a separate turn")
        inventory = enumerate_connected_components(
            arrays["POSITION"],
            triangles,
            mesh_index=mesh_index,
            primitive_index=primitive_index,
        )
        if inventory.truncated:
            raise GlbError("Mesh simplification refuses a truncated component inventory")
        protected = tuple(
            component
            for component in inventory.components
            if component.triangle_count < protected_threshold
        )
        reducible = tuple(
            component
            for component in inventory.components
            if component.triangle_count >= protected_threshold
        )
        if not reducible:
            raise GlbError("Every component is below the mesh-simplification protection threshold")
        protected_triangles = sum(component.triangle_count for component in protected)
        component_targets = _allocated_component_targets(
            [component.triangle_count for component in reducible],
            max(len(reducible), target_triangles - protected_triangles),
        )
        targets_by_id = {
            component.component_id: target
            for component, target in zip(reducible, component_targets, strict=True)
        }
        attribute_accessors = {
            semantic: gltf.accessors[index] for semantic, index in attribute_indices.items()
        }
        output_components: list[npt.NDArray[np.int64]] = []
        maximum_error = 0.0
        for component in inventory.components:
            component_triangles = triangles[np.asarray(component.face_indices, dtype=np.int64)]
            target = targets_by_id.get(component.component_id)
            if target is None:
                output_components.append(component_triangles)
                continue
            used = np.unique(component_triangles.reshape(-1))
            inverse = np.full(position_count, -1, dtype=np.int64)
            inverse[used] = np.arange(len(used), dtype=np.int64)
            local_indices = inverse[component_triangles].astype(np.uint32, copy=False).reshape(-1)
            local_positions = np.ascontiguousarray(
                np.asarray(arrays["POSITION"][used, :3], dtype=np.float32)
            )
            destination = np.empty(len(local_indices), dtype=np.uint32)
            result_error = np.zeros(1, dtype=np.float32)
            metric, weights = _simplification_attribute_metric(
                arrays,
                attribute_accessors,
                used,
            )
            attempted_target = target
            accepted_component: npt.NDArray[np.int64] | None = None
            accepted_error = 0.0
            while accepted_component is None:
                if attempted_target >= len(component_triangles):
                    accepted_component = component_triangles
                    break
                target_index_count = max(3, attempted_target * 3)
                result_error.fill(0.0)
                if metric is not None and weights is not None:
                    result_count = meshoptimizer.simplify_with_attributes(
                        destination,
                        local_indices,
                        local_positions,
                        metric,
                        weights,
                        target_index_count=target_index_count,
                        # meshoptimizer-python 0.2.30a0 omits ctypes argtypes for
                        # meshopt_simplifyWithAttributes, so its otherwise-valid float
                        # argument must carry the C type explicitly.
                        target_error=cast(float, ctypes.c_float(target_error)),
                        result_error=result_error,
                    )
                else:
                    result_count = meshoptimizer.simplify(
                        destination,
                        local_indices,
                        local_positions,
                        target_index_count=target_index_count,
                        target_error=target_error,
                        result_error=result_error,
                    )
                if result_count > 0 and result_count % 3 == 0:
                    simplified_local = destination[:result_count].astype(np.int64, copy=False)
                    candidate_component = used[simplified_local].reshape((-1, 3))
                    generated_degenerate = degenerate_triangle_mask(
                        arrays["POSITION"], candidate_component
                    )
                    if np.any(generated_degenerate):
                        candidate_component = candidate_component[~generated_degenerate]
                    if len(candidate_component):
                        candidate_inventory = enumerate_connected_components(
                            arrays["POSITION"],
                            candidate_component,
                            mesh_index=mesh_index,
                            primitive_index=primitive_index,
                        )
                        bounded_group_count = (
                            candidate_inventory.near_contact_probes[-1].group_count
                            if candidate_inventory.near_contact_probes
                            else candidate_inventory.exact_component_count
                        )
                        if bounded_group_count == 1:
                            accepted_component = candidate_component
                            accepted_error = float(result_error[0])
                            break
                # Back off toward the original component until topology survives. At the
                # source count the exact source faces are retained. This is why the reported
                # result may legitimately stop above the use-case cap.
                attempted_target = min(
                    len(component_triangles),
                    max(
                        attempted_target + 1,
                        (attempted_target + len(component_triangles) + 1) // 2,
                    ),
                )
            output_components.append(accepted_component)
            maximum_error = max(maximum_error, accepted_error)

        simplified_triangles = np.concatenate(output_components, axis=0)
        generated_degenerate = degenerate_triangle_mask(arrays["POSITION"], simplified_triangles)
        if np.any(generated_degenerate):
            simplified_triangles = simplified_triangles[~generated_degenerate]
        if not len(simplified_triangles):
            raise GlbError("Mesh simplification removed every usable triangle")
        if len(simplified_triangles) >= len(triangles):
            raise GlbError("Mesh simplification could not safely reduce any triangles")
        referenced = np.unique(simplified_triangles.reshape(-1))
        old_to_new = np.full(position_count, -1, dtype=np.int64)
        old_to_new[referenced] = np.arange(len(referenced), dtype=np.int64)
        remapped = old_to_new[simplified_triangles].reshape(-1)
        source_position_values = np.asarray(arrays["POSITION"], dtype=np.float64)
        referenced_before = np.unique(triangles)
        before_bounds = np.asarray(
            [
                np.min(source_position_values[referenced_before], axis=0),
                np.max(source_position_values[referenced_before], axis=0),
            ],
            dtype=np.float64,
        )[:, :3]
        after_positions = np.asarray(arrays["POSITION"][referenced, :3], dtype=np.float64)
        after_bounds = np.asarray([after_positions.min(axis=0), after_positions.max(axis=0)])
        tolerance = np.maximum(before_bounds[1] - before_bounds[0], 1e-9) * max_bounds_drift
        if np.any(np.abs(after_bounds - before_bounds) > tolerance):
            raise GlbError("Mesh simplification changed the primitive bounds by more than 2%")
        compacted_triangles = remapped.reshape((-1, 3))
        if np.any(degenerate_triangle_mask(after_positions, compacted_triangles)):
            raise GlbError("Mesh simplification retained a degenerate triangle")
        after_inventory = enumerate_connected_components(
            after_positions,
            compacted_triangles,
            mesh_index=mesh_index,
            primitive_index=primitive_index,
        )
        before_group_count = (
            inventory.near_contact_probes[-1].group_count
            if inventory.near_contact_probes
            else inventory.exact_component_count
        )
        after_group_count = (
            after_inventory.near_contact_probes[-1].group_count
            if after_inventory.near_contact_probes
            else after_inventory.exact_component_count
        )
        if after_group_count != before_group_count:
            raise GlbError("Mesh simplification changed the bounded near-contact component groups")

        for semantic, accessor_index in sorted(attribute_indices.items()):
            accessor = gltf.accessors[accessor_index]
            compacted = np.ascontiguousarray(arrays[semantic][referenced])
            accessor.count = len(compacted)
            _refresh_accessor_bounds(accessor, compacted)
            view_index = cast(int, accessor.bufferView)
            replacements[view_index] = compacted.tobytes(order="C")
        if len(referenced) <= 255:
            packed_indices = remapped.astype(np.uint8, copy=False).reshape((-1, 1))
            component_type = 5121
        elif len(referenced) <= 65535:
            packed_indices = remapped.astype(np.uint16, copy=False).reshape((-1, 1))
            component_type = 5123
        else:
            packed_indices = remapped.astype(np.uint32, copy=False).reshape((-1, 1))
            component_type = 5125
        index_accessor = gltf.accessors[primitive.indices]
        index_accessor.componentType = component_type
        index_accessor.count = len(packed_indices)
        index_accessor.min = [int(remapped.min())]
        index_accessor.max = [int(remapped.max())]
        replacements[cast(int, index_accessor.bufferView)] = packed_indices.tobytes(order="C")
        results[(mesh_index, primitive_index)] = PrimitiveSimplificationResult(
            before_triangles=len(triangles),
            after_triangles=len(simplified_triangles),
            before_positions=position_count,
            after_positions=len(referenced),
            protected_components=len(protected),
            result_error=maximum_error,
        )

    _compact_primary_buffer(gltf, original_blob, replacements)
    return results


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
