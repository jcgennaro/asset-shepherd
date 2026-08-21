"""Low-level GLB access used by the deterministic asset core."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
from pygltflib import FLOAT, GLTF2, TRIANGLE_FAN, TRIANGLE_STRIP, TRIANGLES, Node
from pygltflib.validator import validate as validate_gltf

FloatArray = npt.NDArray[np.float64]


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
    """Compute active-scene bounds by transforming every POSITION accessor."""
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
