"""Acceptance tests for deterministic mesh topology and efficiency measurements."""

import numpy as np

from asset_shepherd.mesh_diagnostics import analyze_mesh_topology


def test_closed_tetrahedron_is_one_consistently_wound_component() -> None:
    """A closed reference shell has no boundary, manifold, or winding defect."""
    positions = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        dtype=np.float32,
    )
    triangles = np.array(
        [[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]],
        dtype=np.int64,
    )

    result = analyze_mesh_topology(positions, triangles)

    assert result.valid_triangle_count == 4
    assert result.boundary_edge_count == 0
    assert result.non_manifold_edge_count == 0
    assert result.inconsistent_winding_edge_count == 0
    assert result.connected_component_count == 1
    assert result.average_vertex_reuse == 3.0


def test_edge_defects_and_wasted_positions_are_counted_without_mutation() -> None:
    """Shared-edge incidence, winding, duplicates, and unused data remain objective facts."""
    positions = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, 1]],
        dtype=np.float32,
    )
    triangles = np.array(
        [[0, 1, 2], [0, 1, 3], [1, 0, 4]],
        dtype=np.int64,
    )

    result = analyze_mesh_topology(positions, triangles)

    assert result.non_manifold_edge_count == 1
    assert result.inconsistent_winding_edge_count == 0
    assert result.connected_component_count == 1
    assert result.unused_position_count == 1
    assert result.duplicate_position_count == 1


def test_fifo_cache_metric_exposes_unreused_triangle_streams() -> None:
    """A fully unshared triangle stream reaches the FIFO-16 worst-case ACMR of three."""
    positions = np.arange(900, dtype=np.float32).reshape((300, 3))
    triangles = np.arange(300, dtype=np.int64).reshape((100, 3))

    result = analyze_mesh_topology(positions, triangles)

    assert result.vertex_cache_acmr == 3.0
    assert result.average_vertex_reuse == 1.0
    assert result.connected_component_count == 100
