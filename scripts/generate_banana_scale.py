"""Generate the small, deterministic banana-for-scale viewer asset."""

from pathlib import Path

import numpy as np
import trimesh


def _banana_body() -> tuple[trimesh.Trimesh, tuple[np.ndarray, np.ndarray]]:
    """Build a tapered 20-centimeter curved tube and return its endpoint centers."""
    segment_count = 32
    ring_count = 12
    curve_radius_m = 0.09
    half_angle = np.deg2rad(65.0)
    angles = np.linspace(-half_angle, half_angle, segment_count)
    vertices: list[np.ndarray] = []

    centers = tuple(
        np.array(
            [
                curve_radius_m * np.sin(angle),
                curve_radius_m * (1.0 - np.cos(angle)),
                0.0,
            ],
            dtype=np.float64,
        )
        for angle in angles
    )
    for index, (angle, center) in enumerate(zip(angles, centers, strict=True)):
        normalized = abs((index / (segment_count - 1)) * 2.0 - 1.0)
        radius_m = 0.004 + 0.012 * (1.0 - normalized**2)
        curve_normal = np.array([-np.sin(angle), np.cos(angle), 0.0], dtype=np.float64)
        binormal = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        for ring_index in range(ring_count):
            phase = 2.0 * np.pi * ring_index / ring_count
            vertices.append(
                center + radius_m * (np.cos(phase) * curve_normal + np.sin(phase) * binormal)
            )

    faces: list[tuple[int, int, int]] = []
    for segment_index in range(segment_count - 1):
        for ring_index in range(ring_count):
            next_ring = (ring_index + 1) % ring_count
            current = segment_index * ring_count + ring_index
            current_next = segment_index * ring_count + next_ring
            following = (segment_index + 1) * ring_count + ring_index
            following_next = (segment_index + 1) * ring_count + next_ring
            faces.extend(
                ((current, following, following_next), (current, following_next, current_next))
            )

    body = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    body.visual.vertex_colors = np.tile(
        np.array([244, 194, 54, 255], dtype=np.uint8),
        (len(body.vertices), 1),
    )
    return body, (centers[0], centers[-1])


def generate_banana(destination: Path) -> None:
    """Write one reproducible stylized banana GLB at normal banana scale."""
    body, endpoints = _banana_body()
    scene = trimesh.Scene()
    scene.add_geometry(body, node_name="BananaBody", geom_name="BananaBody")
    for index, endpoint in enumerate(endpoints):
        tip = trimesh.creation.icosphere(subdivisions=2, radius=0.005)
        tip.apply_translation(endpoint)
        tip.visual.vertex_colors = np.tile(
            np.array([104, 69, 35, 255], dtype=np.uint8),
            (len(tip.vertices), 1),
        )
        scene.add_geometry(tip, node_name=f"BananaTip_{index}", geom_name=f"BananaTip_{index}")
    exported = scene.export(file_type="glb")
    if not isinstance(exported, bytes):
        raise TypeError("Trimesh did not return binary GLB data")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(exported)


def main() -> None:
    """Generate the committed browser reference asset."""
    project_root = Path(__file__).resolve().parents[1]
    generate_banana(project_root / "src" / "asset_shepherd" / "static" / "banana-scale.glb")


if __name__ == "__main__":
    main()
