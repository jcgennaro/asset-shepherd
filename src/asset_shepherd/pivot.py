"""Deterministic, source-bound pivot anchor sensing."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from hashlib import sha256
from itertools import product
from pathlib import Path
from typing import Literal, cast

import numpy as np
import numpy.typing as npt
from pygltflib import GLTF2, TRIANGLE_FAN, TRIANGLE_STRIP, TRIANGLES

from asset_shepherd.glb import GlbError, accessor_array, iter_world_matrices, load_glb
from asset_shepherd.models import (
    Bounds3D,
    InspectionResult,
    PivotAnchorCandidate,
    PivotAnchorInventory,
)

PivotAnchorKind = Literal[
    "AUTHORED_ORIGIN",
    "BOUNDS_CENTER",
    "FOOTPRINT_CENTER_BOTTOM",
    "BOUNDS_CORNER",
    "SURFACE_AREA_CENTROID",
    "VOLUME_CENTROID",
    "LONG_AXIS_END_REGION",
]


def _bounds_model(minimum: np.ndarray, maximum: np.ndarray) -> Bounds3D:
    dimensions = maximum - minimum
    minimum_m = tuple(float(value) for value in minimum)
    maximum_m = tuple(float(value) for value in maximum)
    dimensions_m = tuple(float(value) for value in dimensions)
    return Bounds3D(
        minimum_m=cast(tuple[float, float, float], minimum_m),
        maximum_m=cast(tuple[float, float, float], maximum_m),
        dimensions_m=cast(tuple[float, float, float], dimensions_m),
        minimum_cm=cast(tuple[float, float, float], tuple(value * 100.0 for value in minimum_m)),
        maximum_cm=cast(tuple[float, float, float], tuple(value * 100.0 for value in maximum_m)),
        dimensions_cm=cast(
            tuple[float, float, float], tuple(value * 100.0 for value in dimensions_m)
        ),
    )


def _triangle_indices(gltf: GLTF2, mesh_index: int, primitive_index: int) -> np.ndarray:
    primitive = gltf.meshes[mesh_index].primitives[primitive_index]
    position_index = cast(object, primitive.attributes.POSITION)
    if not isinstance(position_index, int):
        raise GlbError("Mesh primitive has no POSITION accessor")
    position_count = len(accessor_array(gltf, position_index))
    if primitive.indices is None:
        indices = np.arange(position_count, dtype=np.int64)
    else:
        indices = np.asarray(accessor_array(gltf, primitive.indices), dtype=np.int64).reshape(-1)
    if np.any(indices < 0) or np.any(indices >= position_count):
        raise GlbError("Mesh primitive contains an out-of-range vertex index")
    mode = primitive.mode if primitive.mode is not None else TRIANGLES
    if mode == TRIANGLES:
        usable = len(indices) - (len(indices) % 3)
        return indices[:usable].reshape((-1, 3))
    if mode == TRIANGLE_STRIP and len(indices) >= 3:
        triangles = np.column_stack((indices[:-2], indices[1:-1], indices[2:]))
        odd = triangles[1::2].copy()
        triangles[1::2, 0] = odd[:, 1]
        triangles[1::2, 1] = odd[:, 0]
        return triangles
    if mode == TRIANGLE_FAN and len(indices) >= 3:
        return np.column_stack(
            (
                np.full(len(indices) - 2, indices[0], dtype=indices.dtype),
                indices[1:-1],
                indices[2:],
            )
        )
    return np.empty((0, 3), dtype=np.int64)


def _world_triangles(gltf: GLTF2) -> npt.NDArray[np.float64]:
    triangles: list[npt.NDArray[np.float64]] = []
    for node_index, world in iter_world_matrices(gltf):
        mesh_index = gltf.nodes[node_index].mesh
        if mesh_index is None:
            continue
        for primitive_index, primitive in enumerate(gltf.meshes[mesh_index].primitives):
            position_index = cast(object, primitive.attributes.POSITION)
            if not isinstance(position_index, int):
                raise GlbError("Mesh primitive has no POSITION accessor")
            positions = accessor_array(gltf, position_index).astype(np.float64)[:, :3]
            homogeneous = np.column_stack((positions, np.ones(len(positions), dtype=np.float64)))
            world_positions = (world @ homogeneous.T).T[:, :3]
            indices = _triangle_indices(gltf, mesh_index, primitive_index)
            if len(indices):
                triangles.append(world_positions[indices])
    if not triangles:
        raise GlbError("The active scene has no supported triangles for pivot sensing")
    combined = np.concatenate(triangles, axis=0)
    finite = np.isfinite(combined).all(axis=(1, 2))
    area_vectors = np.cross(combined[:, 1] - combined[:, 0], combined[:, 2] - combined[:, 0])
    nondegenerate = np.linalg.norm(area_vectors, axis=1) > 1e-15
    result = combined[finite & nondegenerate]
    if not len(result):
        raise GlbError("The active scene has no finite non-degenerate triangles for pivot sensing")
    return result


def _relative(
    position: np.ndarray,
    minimum: np.ndarray,
    dimensions: np.ndarray,
) -> tuple[float, float, float]:
    values = np.divide(
        position - minimum,
        dimensions,
        out=np.zeros(3, dtype=np.float64),
        where=dimensions > 0,
    )
    return (float(values[0]), float(values[1]), float(values[2]))


def _anchor_id(source_sha256: str, kind: str, label: str, position: np.ndarray) -> str:
    rounded = ",".join(f"{float(value):.12g}" for value in position)
    digest = sha256(f"{source_sha256}|{kind}|{label}|{rounded}".encode()).hexdigest()[:16]
    return f"pivot-anchor-{digest}-v1"


def _candidate(
    *,
    source_sha256: str,
    kind: PivotAnchorKind,
    label: str,
    position: np.ndarray,
    minimum: np.ndarray,
    dimensions: np.ndarray,
    evidence: str,
    region_bounds: Bounds3D | None = None,
) -> PivotAnchorCandidate:
    return PivotAnchorCandidate(
        anchor_id=_anchor_id(source_sha256, kind, label, position),
        kind=kind,
        label=label,
        position_m=(float(position[0]), float(position[1]), float(position[2])),
        bounds_relative_position=_relative(position, minimum, dimensions),
        region_bounds=region_bounds,
        evidence=evidence,
    )


def _volume_centroid_allowed(inspection: InspectionResult) -> bool:
    diagnostics = inspection.diagnostics
    if diagnostics is None or not diagnostics.primitives:
        return False
    return all(
        primitive.topology_analyzed
        and primitive.valid_triangle_count > 0
        and primitive.virtual_weld_boundary_edge_count == 0
        and primitive.virtual_weld_non_manifold_edge_count == 0
        and primitive.virtual_weld_inconsistent_winding_edge_count == 0
        for primitive in diagnostics.primitives
    )


def inspect_pivot_anchors(source: Path, inspection: InspectionResult) -> PivotAnchorInventory:
    """Return stable, measured origin candidates without accepting arbitrary coordinates."""
    if inspection.geometry is None:
        raise GlbError("Pivot sensing requires measured geometry")
    gltf = load_glb(source)
    triangles = _world_triangles(gltf)
    bounds = inspection.geometry.bounds
    minimum = np.asarray(bounds.minimum_m, dtype=np.float64)
    maximum = np.asarray(bounds.maximum_m, dtype=np.float64)
    dimensions = maximum - minimum
    source_sha256 = inspection.package.file_sha256
    candidates: list[PivotAnchorCandidate] = []

    authored_origin = np.zeros(3, dtype=np.float64)
    candidates.append(
        _candidate(
            source_sha256=source_sha256,
            kind="AUTHORED_ORIGIN",
            label="authored origin",
            position=authored_origin,
            minimum=minimum,
            dimensions=dimensions,
            evidence="The point is the origin authored in the current GLB coordinate system.",
        )
    )

    bounds_center = (minimum + maximum) / 2.0
    candidates.append(
        _candidate(
            source_sha256=source_sha256,
            kind="BOUNDS_CENTER",
            label="world-bounds center",
            position=bounds_center,
            minimum=minimum,
            dimensions=dimensions,
            evidence="The point is the exact center of the referenced world-space bounds.",
        )
    )
    footprint_center = np.asarray(
        [bounds_center[0], minimum[1], bounds_center[2]], dtype=np.float64
    )
    candidates.append(
        _candidate(
            source_sha256=source_sha256,
            kind="FOOTPRINT_CENTER_BOTTOM",
            label="footprint center-bottom",
            position=footprint_center,
            minimum=minimum,
            dimensions=dimensions,
            evidence="The point centers X/Z and lies on the minimum-Y ground plane.",
        )
    )

    for x_side, y_side, z_side in product((0, 1), repeat=3):
        sides = (x_side, y_side, z_side)
        point = np.asarray(
            [maximum[index] if side else minimum[index] for index, side in enumerate(sides)],
            dtype=np.float64,
        )
        label = "bounds corner " + " / ".join(
            f"{axis}-{'max' if side else 'min'}"
            for axis, side in zip(("X", "Y", "Z"), sides, strict=True)
        )
        candidates.append(
            _candidate(
                source_sha256=source_sha256,
                kind="BOUNDS_CORNER",
                label=label,
                position=point,
                minimum=minimum,
                dimensions=dimensions,
                evidence="The point is one exact corner of the referenced world-space bounds.",
            )
        )

    doubled_areas = np.linalg.norm(
        np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1
    )
    triangle_centers = triangles.mean(axis=1)
    surface_centroid = np.average(triangle_centers, axis=0, weights=doubled_areas)
    candidates.append(
        _candidate(
            source_sha256=source_sha256,
            kind="SURFACE_AREA_CENTROID",
            label="surface-area centroid",
            position=surface_centroid,
            minimum=minimum,
            dimensions=dimensions,
            evidence=(
                "The point is the triangle-area-weighted center of the referenced visible surface; "
                "it is not a physical center of mass."
            ),
        )
    )

    longest_axis = int(np.argmax(dimensions))
    axis_name = ("X", "Y", "Z")[longest_axis]
    region_fraction = 0.25
    center_coordinates = triangle_centers[:, longest_axis]
    for side_name, mask in (
        (
            "min",
            center_coordinates
            <= minimum[longest_axis] + dimensions[longest_axis] * region_fraction,
        ),
        (
            "max",
            center_coordinates
            >= maximum[longest_axis] - dimensions[longest_axis] * region_fraction,
        ),
    ):
        if not np.any(mask):
            continue
        point = np.average(triangle_centers[mask], axis=0, weights=doubled_areas[mask])
        region_points = triangles[mask].reshape((-1, 3))
        region_bounds = _bounds_model(region_points.min(axis=0), region_points.max(axis=0))
        candidates.append(
            _candidate(
                source_sha256=source_sha256,
                kind="LONG_AXIS_END_REGION",
                label=f"{axis_name}-{side_name} end-region surface center",
                position=point,
                minimum=minimum,
                dimensions=dimensions,
                region_bounds=region_bounds,
                evidence=(
                    f"The point is the area-weighted center of triangles in the outer 25% of the "
                    f"bounds along the longest ({axis_name}) axis. The region bounds let visual "
                    "evidence identify which semantic feature occupies that end."
                ),
            )
        )

    notes: list[str] = [
        "Surface and end-region centers are geometric landmarks, not semantic conclusions; "
        "the agent must match them to coordinate-labeled views.",
        "Bounding-box corners are exact snap points but do not imply the intended placement.",
    ]
    if _volume_centroid_allowed(inspection):
        signed_six_volumes = np.einsum(
            "ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])
        )
        signed_volume_sum = float(signed_six_volumes.sum())
        bounds_volume = float(np.prod(dimensions))
        if abs(signed_volume_sum) > max(bounds_volume * 6.0e-12, 1.0e-18):
            volume_numerator = cast(
                npt.NDArray[np.float64],
                np.sum(
                    (triangles[:, 0] + triangles[:, 1] + triangles[:, 2])
                    * signed_six_volumes[:, None],
                    axis=0,
                ),
            )
            volume_centroid = volume_numerator / (4.0 * signed_volume_sum)
            if np.isfinite(volume_centroid).all():
                candidates.append(
                    _candidate(
                        source_sha256=source_sha256,
                        kind="VOLUME_CENTROID",
                        label="uniform-volume centroid",
                        position=volume_centroid,
                        minimum=minimum,
                        dimensions=dimensions,
                        evidence=(
                            "The point is the signed-volume centroid of a closed, manifold, "
                            "consistently wound surface. It assumes uniform density."
                        ),
                    )
                )
        else:
            notes.append(
                "Volume centroid omitted because the closed surface has negligible signed volume."
            )
    else:
        notes.append(
            "Volume centroid omitted because virtual-weld topology is not proven closed, "
            "manifold, and consistently wound."
        )

    return PivotAnchorInventory(
        source_sha256=source_sha256,
        bounds=bounds,
        candidates=tuple(candidates),
        notes=tuple(notes),
    )
