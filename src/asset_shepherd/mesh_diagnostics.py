"""Deterministic topology and GPU-efficiency measurements for triangle meshes."""

from __future__ import annotations

from dataclasses import dataclass

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


def _connected_face_components(
    inverse_edges: npt.NDArray[np.int64],
    edge_counts: npt.NDArray[np.int64],
    face_indices: npt.NDArray[np.int64],
    face_count: int,
) -> int:
    """Count edge-connected face components with a compact union-find pass."""
    if face_count == 0:
        return 0
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
    return len({find(index) for index in range(face_count)})


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
