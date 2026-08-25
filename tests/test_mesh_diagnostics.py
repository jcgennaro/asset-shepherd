"""Acceptance tests for deterministic mesh topology and efficiency measurements."""

import numpy as np

from asset_shepherd.mesh_diagnostics import analyze_duplicate_positions, analyze_mesh_topology


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


def test_virtual_weld_distinguishes_attribute_seams_from_safe_duplicates() -> None:
    """Position topology is projected while UV-crossing merges remain protected."""
    positions = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0], [1, 1, 0]],
        dtype=np.float32,
    )
    triangles = np.array([[0, 1, 2], [3, 2, 4]], dtype=np.int64)
    normals = np.tile(np.array([[0, 0, 1]], dtype=np.float32), (5, 1))
    uv_seam = np.array(
        [[0, 0], [1, 0], [0, 1], [0.5, 0.5], [1, 1]],
        dtype=np.float32,
    )

    protected = analyze_duplicate_positions(
        positions,
        triangles,
        {"NORMAL": normals, "TEXCOORD_0": uv_seam},
    )
    safe_uv = uv_seam.copy()
    safe_uv[3] = safe_uv[0]
    safe = analyze_duplicate_positions(
        positions,
        triangles,
        {"NORMAL": normals, "TEXCOORD_0": safe_uv},
    )

    assert protected.duplicate_position_count == 1
    assert protected.virtual_weld_position_count == 4
    assert protected.attribute_safe_merge_count == 0
    assert protected.protected_duplicate_count == 1
    assert protected.protected_attribute_conflicts == ("TEXCOORD_0",)
    assert safe.attribute_safe_merge_count == 1
    assert safe.protected_duplicate_count == 0
