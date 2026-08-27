"""Deterministic topology and GPU-efficiency measurements for triangle meshes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class MeshTopologyMeasurements:
    """Profile-free facts; the workflow agent decides their target-specific significance."""

    valid_triangle_count: int
    boundary_edge_count: int
    non_manifold_edge_count: int
    inconsistent_winding_edge_count: int
    connected_component_count: int
    unused_position_count: int
    duplicate_position_count: int
    average_vertex_reuse: float
    vertex_cache_acmr: float


@dataclass(frozen=True)
class DuplicatePositionMeasurements:
    """Exact-position weld projection with protected-attribute conflict evidence."""

    duplicate_position_count: int
    coincident_position_group_count: int
    virtual_weld_position_count: int
    virtual_weld_boundary_edge_count: int
    virtual_weld_non_manifold_edge_count: int
    virtual_weld_inconsistent_winding_edge_count: int
    virtual_weld_connected_component_count: int
    virtual_weld_degenerate_triangle_count: int
    attribute_safe_merge_count: int
    protected_duplicate_count: int
    protected_attribute_conflicts: tuple[str, ...]


@dataclass(frozen=True)
class NearContactProbe:
    """One non-authoritative grouping result at a scale-relative separation tolerance."""

    tolerance_m: float
    group_count: int


@dataclass(frozen=True)
class ConnectedComponentMeasurement:
    """One exact position-projected, edge-connected triangle component."""

    component_id: str
    ordinal: int
    face_indices: tuple[int, ...]
    triangle_count: int
    referenced_position_count: int
    minimum_m: tuple[float, float, float]
    maximum_m: tuple[float, float, float]
    centroid_m: tuple[float, float, float]
    triangle_fraction: float
    near_contact_group: int


@dataclass(frozen=True)
class ConnectedComponentInventory:
    """Bounded exact components plus diagnostic near-contact grouping evidence."""

    exact_component_count: int
    components: tuple[ConnectedComponentMeasurement, ...]
    near_contact_probes: tuple[NearContactProbe, ...]
    truncated: bool


def _row_keys(values: npt.NDArray[np.generic]) -> list[bytes]:
    """Return stable exact byte keys without coercing integer attributes to floats."""
    contiguous = np.ascontiguousarray(values)
    return [contiguous[index].tobytes() for index in range(len(contiguous))]


def _group_inverse(keys: list[bytes]) -> tuple[npt.NDArray[np.int64], int]:
    """Map byte-identical rows to deterministic first-seen group indices."""
    groups: dict[bytes, int] = {}
    inverse = np.empty(len(keys), dtype=np.int64)
    for index, key in enumerate(keys):
        group = groups.get(key)
        if group is None:
            group = len(groups)
            groups[key] = group
        inverse[index] = group
    return inverse, len(groups)


def analyze_duplicate_positions(
    positions: npt.NDArray[np.generic],
    triangles: npt.NDArray[np.int64],
    attributes: dict[str, npt.NDArray[np.generic]],
) -> DuplicatePositionMeasurements:
    """Project exact-position welding and prove which merges preserve every attribute.

    The virtual projection intentionally ignores vertex-attribute seams so an agent can distinguish
    split glTF tuples from the underlying position topology.  The safe count is stricter: vertices
    are mergeable only when every supplied attribute row is byte-identical.
    """
    position_values = np.asarray(positions)[:, :3]
    position_keys = _row_keys(position_values)
    position_inverse, position_group_count = _group_inverse(position_keys)
    duplicate_count = len(position_values) - position_group_count
    group_sizes = np.bincount(position_inverse, minlength=position_group_count)
    coincident_groups = int(np.count_nonzero(group_sizes > 1))

    triangle_indices = np.asarray(triangles, dtype=np.int64).reshape((-1, 3))
    projected = position_inverse[triangle_indices] if len(triangle_indices) else triangle_indices
    projected_degenerate = (
        (projected[:, 0] == projected[:, 1])
        | (projected[:, 1] == projected[:, 2])
        | (projected[:, 0] == projected[:, 2])
        if len(projected)
        else np.zeros(0, dtype=bool)
    )
    representative_indices = np.full(position_group_count, -1, dtype=np.int64)
    for index, group in enumerate(position_inverse):
        if representative_indices[group] < 0:
            representative_indices[group] = index
    projected_topology = analyze_mesh_topology(
        position_values[representative_indices],
        projected[~projected_degenerate],
    )

    ordered_semantics = tuple(sorted(attributes))
    protected_keys: list[bytes] = []
    attribute_keys = {semantic: _row_keys(attributes[semantic]) for semantic in ordered_semantics}
    for index, position_key in enumerate(position_keys):
        protected_keys.append(
            b"".join(
                (
                    len(position_key).to_bytes(4, "little"),
                    position_key,
                    *(
                        len(attribute_keys[semantic][index]).to_bytes(4, "little")
                        + attribute_keys[semantic][index]
                        for semantic in ordered_semantics
                    ),
                )
            )
        )
    _, protected_group_count = _group_inverse(protected_keys)
    safe_merge_count = len(position_values) - protected_group_count

    conflicts: list[str] = []
    duplicate_group_ids = np.flatnonzero(group_sizes > 1)
    for semantic in ordered_semantics:
        keys = attribute_keys[semantic]
        if any(
            len({keys[int(index)] for index in np.flatnonzero(position_inverse == group)}) > 1
            for group in duplicate_group_ids
        ):
            conflicts.append(semantic)

    return DuplicatePositionMeasurements(
        duplicate_position_count=duplicate_count,
        coincident_position_group_count=coincident_groups,
        virtual_weld_position_count=position_group_count,
        virtual_weld_boundary_edge_count=projected_topology.boundary_edge_count,
        virtual_weld_non_manifold_edge_count=projected_topology.non_manifold_edge_count,
        virtual_weld_inconsistent_winding_edge_count=(
            projected_topology.inconsistent_winding_edge_count
        ),
        virtual_weld_connected_component_count=projected_topology.connected_component_count,
        virtual_weld_degenerate_triangle_count=int(np.count_nonzero(projected_degenerate)),
        attribute_safe_merge_count=safe_merge_count,
        protected_duplicate_count=duplicate_count - safe_merge_count,
        protected_attribute_conflicts=tuple(conflicts),
    )


def attribute_safe_weld_mapping(
    positions: npt.NDArray[np.generic],
    attributes: dict[str, npt.NDArray[np.generic]],
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    """Return old-to-new indices and representatives for byte-identical vertex tuples."""
    position_keys = _row_keys(np.asarray(positions)[:, :3])
    ordered_semantics = tuple(sorted(attributes))
    attribute_keys = {semantic: _row_keys(attributes[semantic]) for semantic in ordered_semantics}
    complete_keys = [
        b"".join(
            (
                position_keys[index],
                *(
                    len(attribute_keys[semantic][index]).to_bytes(4, "little")
                    + attribute_keys[semantic][index]
                    for semantic in ordered_semantics
                ),
            )
        )
        for index in range(len(position_keys))
    ]
    inverse, group_count = _group_inverse(complete_keys)
    representatives = np.full(group_count, -1, dtype=np.int64)
    for index, group in enumerate(inverse):
        if representatives[group] < 0:
            representatives[group] = index
    return inverse, representatives


def _face_component_labels(
    inverse_edges: npt.NDArray[np.int64],
    edge_counts: npt.NDArray[np.int64],
    face_indices: npt.NDArray[np.int64],
    face_count: int,
) -> npt.NDArray[np.int64]:
    """Assign deterministic edge-connected component labels with union-find."""
    if face_count == 0:
        return np.empty(0, dtype=np.int64)
    parents = np.arange(face_count, dtype=np.int64)

    def find(value: int) -> int:
        while int(parents[value]) != value:
            parents[value] = parents[int(parents[value])]
            value = int(parents[value])
        return value

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    order = np.argsort(inverse_edges, kind="stable")
    ordered_faces = face_indices[order]
    start = 0
    for count in edge_counts:
        end = start + int(count)
        if count >= 2:
            first = int(ordered_faces[start])
            for face in ordered_faces[start + 1 : end]:
                union(first, int(face))
        start = end
    roots = np.asarray([find(index) for index in range(face_count)], dtype=np.int64)
    ordered_roots = sorted(
        set(int(value) for value in roots), key=lambda root: int(np.flatnonzero(roots == root)[0])
    )
    root_to_label = {root: index for index, root in enumerate(ordered_roots)}
    return np.asarray([root_to_label[int(root)] for root in roots], dtype=np.int64)


def _connected_face_components(
    inverse_edges: npt.NDArray[np.int64],
    edge_counts: npt.NDArray[np.int64],
    face_indices: npt.NDArray[np.int64],
    face_count: int,
) -> int:
    """Count edge-connected face components with a compact union-find pass."""
    labels = _face_component_labels(inverse_edges, edge_counts, face_indices, face_count)
    return int(labels.max(initial=-1)) + 1


def _vertex_connected_face_labels(
    triangles: npt.NDArray[np.int64],
) -> npt.NDArray[np.int64]:
    """Assign body labels where faces sharing any projected position stay together."""
    face_count = len(triangles)
    if face_count == 0:
        return np.empty(0, dtype=np.int64)
    parents = np.arange(face_count, dtype=np.int64)

    def find(value: int) -> int:
        while int(parents[value]) != value:
            parents[value] = parents[int(parents[value])]
            value = int(parents[value])
        return value

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    first_face_by_position: dict[int, int] = {}
    for face_index, triangle in enumerate(triangles):
        for position_index in triangle:
            key = int(position_index)
            first_face = first_face_by_position.setdefault(key, face_index)
            union(first_face, face_index)
    roots = np.asarray([find(index) for index in range(face_count)], dtype=np.int64)
    ordered_roots = sorted(
        set(int(value) for value in roots),
        key=lambda root: int(np.flatnonzero(roots == root)[0]),
    )
    root_to_label = {root: index for index, root in enumerate(ordered_roots)}
    return np.asarray([root_to_label[int(root)] for root in roots], dtype=np.int64)


def _near_contact_labels(
    bounds: tuple[tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]], ...],
    tolerance: float,
) -> npt.NDArray[np.int64]:
    """Group component AABBs separated by no more than a diagnostic tolerance."""
    parents = np.arange(len(bounds), dtype=np.int64)

    def find(value: int) -> int:
        while int(parents[value]) != value:
            parents[value] = parents[int(parents[value])]
            value = int(parents[value])
        return value

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_index, (left_minimum, left_maximum) in enumerate(bounds):
        for right_index in range(left_index + 1, len(bounds)):
            right_minimum, right_maximum = bounds[right_index]
            separation = np.maximum(
                np.maximum(left_minimum - right_maximum, right_minimum - left_maximum),
                0.0,
            )
            if float(np.linalg.norm(separation)) <= tolerance:
                union(left_index, right_index)
    roots = [find(index) for index in range(len(bounds))]
    ordered_roots = sorted(set(roots), key=roots.index)
    root_to_label = {root: index for index, root in enumerate(ordered_roots)}
    return np.asarray([root_to_label[root] for root in roots], dtype=np.int64)


def enumerate_connected_components(
    positions: npt.NDArray[np.generic],
    triangles: npt.NDArray[np.int64],
    *,
    mesh_index: int,
    primitive_index: int,
    limit: int = 128,
) -> ConnectedComponentInventory:
    """Enumerate exact components and bounded, non-mutating near-contact hints.

    Exact byte-identical positions are projected before edge connectivity is measured so ordinary
    UV and hard-normal seams do not become false bodies. Near-contact probes group component AABBs
    only for agent/human interpretation; their tolerance never changes geometry or authorizes a
    deletion.
    """
    triangle_values = np.asarray(triangles, dtype=np.int64).reshape((-1, 3))
    if not len(triangle_values):
        return ConnectedComponentInventory(0, (), (), False)
    position_values = np.asarray(positions)[:, :3].astype(np.float64, copy=False)
    position_inverse, _ = _group_inverse(_row_keys(np.asarray(positions)[:, :3]))
    projected = position_inverse[triangle_values]
    labels = _vertex_connected_face_labels(projected)
    component_count = int(labels.max(initial=-1)) + 1
    truncated = component_count > limit
    measured_count = min(component_count, limit)
    face_groups = tuple(np.flatnonzero(labels == ordinal) for ordinal in range(measured_count))
    component_bounds: list[tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]] = []
    component_positions: list[npt.NDArray[np.float64]] = []
    for faces in face_groups:
        referenced = np.unique(triangle_values[faces].reshape(-1))
        values = position_values[referenced]
        component_positions.append(values)
        component_bounds.append((values.min(axis=0), values.max(axis=0)))

    finite = position_values[np.isfinite(position_values).all(axis=1)]
    diagonal = float(np.linalg.norm(np.ptp(finite, axis=0))) if len(finite) else 0.0
    absolute_scale = float(np.max(np.abs(finite), initial=0.0)) if len(finite) else 0.0
    numeric_floor = max(absolute_scale, diagonal, 1.0) * np.finfo(np.float32).eps * 8.0
    tolerance_candidates = tuple(
        sorted(
            {
                max(numeric_floor, diagonal * multiplier)
                for multiplier in (1e-7, 1e-6, 1e-5, 1e-4, 1e-3)
            }
        )
    )
    near_labels = np.arange(measured_count, dtype=np.int64)
    probes: list[NearContactProbe] = []
    if not truncated and measured_count:
        for tolerance in tolerance_candidates:
            near_labels = _near_contact_labels(tuple(component_bounds), float(tolerance))
            probes.append(
                NearContactProbe(
                    tolerance_m=float(tolerance),
                    group_count=int(near_labels.max(initial=-1)) + 1,
                )
            )

    components: list[ConnectedComponentMeasurement] = []
    for ordinal, (faces, values, (minimum, maximum)) in enumerate(
        zip(face_groups, component_positions, component_bounds, strict=True)
    ):
        canonical_membership = np.ascontiguousarray(triangle_values[faces], dtype="<i8").tobytes()
        digest = sha256(canonical_membership).hexdigest()[:8]
        component_id = f"component-m{mesh_index:03d}-p{primitive_index:03d}-c{ordinal:03d}-{digest}"
        referenced = np.unique(triangle_values[faces].reshape(-1))
        centroid = values.mean(axis=0)
        components.append(
            ConnectedComponentMeasurement(
                component_id=component_id,
                ordinal=ordinal,
                face_indices=tuple(int(value) for value in faces),
                triangle_count=len(faces),
                referenced_position_count=len(referenced),
                minimum_m=(float(minimum[0]), float(minimum[1]), float(minimum[2])),
                maximum_m=(float(maximum[0]), float(maximum[1]), float(maximum[2])),
                centroid_m=(float(centroid[0]), float(centroid[1]), float(centroid[2])),
                triangle_fraction=len(faces) / len(triangle_values),
                near_contact_group=int(near_labels[ordinal]) if len(near_labels) else ordinal,
            )
        )
    return ConnectedComponentInventory(
        exact_component_count=component_count,
        components=tuple(components),
        near_contact_probes=tuple(probes),
        truncated=truncated,
    )


def _fifo_vertex_cache_acmr(indices: npt.NDArray[np.int64], triangle_count: int) -> float:
    """Estimate post-transform locality with meshoptimizer's conventional FIFO-16 model."""
    if triangle_count == 0:
        return 0.0
    cache: list[int] = []
    cached: set[int] = set()
    misses = 0
    for raw_index in indices:
        index = int(raw_index)
        if index in cached:
            continue
        misses += 1
        cache.append(index)
        cached.add(index)
        if len(cache) > 16:
            cached.remove(cache.pop(0))
    return misses / triangle_count


def analyze_mesh_topology(
    positions: npt.NDArray[np.generic],
    triangles: npt.NDArray[np.int64],
) -> MeshTopologyMeasurements:
    """Measure edge topology, fragmentation, redundant data, and index locality."""
    position_count = len(positions)
    if not len(triangles):
        return MeshTopologyMeasurements(
            valid_triangle_count=0,
            boundary_edge_count=0,
            non_manifold_edge_count=0,
            inconsistent_winding_edge_count=0,
            connected_component_count=0,
            unused_position_count=position_count,
            duplicate_position_count=0,
            average_vertex_reuse=0.0,
            vertex_cache_acmr=0.0,
        )

    triangle_indices = np.asarray(triangles, dtype=np.int64).reshape((-1, 3))
    directed_edges = np.concatenate(
        (
            triangle_indices[:, [0, 1]],
            triangle_indices[:, [1, 2]],
            triangle_indices[:, [2, 0]],
        ),
        axis=0,
    )
    canonical_edges = np.sort(directed_edges, axis=1)
    _, inverse, counts = np.unique(
        canonical_edges,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    edge_directions = np.where(
        directed_edges[:, 0] <= directed_edges[:, 1],
        1,
        -1,
    )
    direction_sums = np.bincount(inverse, weights=edge_directions, minlength=len(counts))
    face_indices = np.tile(np.arange(len(triangle_indices), dtype=np.int64), 3)
    used_positions = np.unique(triangle_indices)
    finite_positions = np.asarray(positions)[:, :3]
    finite_positions = finite_positions[np.isfinite(finite_positions).all(axis=1)]
    duplicate_positions = (
        len(finite_positions) - len(np.unique(finite_positions, axis=0))
        if len(finite_positions)
        else 0
    )

    return MeshTopologyMeasurements(
        valid_triangle_count=len(triangle_indices),
        boundary_edge_count=int(np.count_nonzero(counts == 1)),
        non_manifold_edge_count=int(np.count_nonzero(counts > 2)),
        inconsistent_winding_edge_count=int(
            np.count_nonzero((counts == 2) & (np.abs(direction_sums) == 2))
        ),
        connected_component_count=_connected_face_components(
            inverse.astype(np.int64, copy=False),
            counts.astype(np.int64, copy=False),
            face_indices,
            len(triangle_indices),
        ),
        unused_position_count=max(position_count - len(used_positions), 0),
        duplicate_position_count=duplicate_positions,
        average_vertex_reuse=(len(triangle_indices) * 3) / max(len(used_positions), 1),
        vertex_cache_acmr=_fifo_vertex_cache_acmr(triangle_indices.reshape(-1), len(triangles)),
    )
