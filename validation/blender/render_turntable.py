"""Render four neutral evidence views of one GLB in Blender background mode."""

import argparse
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "right": Vector((1.0, 0.0, 0.0)),
    "back": Vector((0.0, 1.0, 0.0)),
    "left": Vector((-1.0, 0.0, 0.0)),
}


def _arguments() -> argparse.Namespace:
    """Parse arguments after Blender's conventional ``--`` delimiter."""
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(arguments)


def _clear_scene() -> None:
    """Clear the temporary evidence scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _mesh_bounds(objects: list[Any]) -> tuple[Vector, Vector]:
    """Return world-space minimum and maximum corners for imported meshes."""
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points:
        raise ValueError("Imported GLB contains no mesh bounds to render")
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return minimum, maximum


def _aim_at(obj: object, target: Vector) -> None:
    """Aim a camera or light's local negative Z axis at a world-space point."""
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _add_area_light(
    name: str,
    location: Vector,
    target: Vector,
    energy: float,
    size: float,
) -> None:
    """Add one soft area light to the evidence rig."""
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    _aim_at(light, target)


def main() -> None:
    """Import, frame, light, and render the four standard views."""
    args = _arguments()
    asset = args.asset.resolve(strict=True)
    output_dir = args.output_dir.resolve(strict=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_scene()
    result = bpy.ops.import_scene.gltf(filepath=str(asset))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender GLB import failed: {sorted(result)}")
    objects = list(bpy.context.scene.objects)
    minimum, maximum = _mesh_bounds(objects)
    center = (minimum + maximum) / 2.0
    dimensions = maximum - minimum
    span = max(dimensions)

    bpy.ops.mesh.primitive_plane_add(size=span * 5.0, location=(center.x, center.y, minimum.z))
    ground = bpy.context.object
    ground.name = "EvidenceGround"
    ground_material = bpy.data.materials.new("EvidenceGroundMaterial")
    ground_material.diffuse_color = (0.12, 0.14, 0.17, 1.0)
    ground.data.materials.append(ground_material)

    target = Vector((center.x, center.y, minimum.z + dimensions.z * 0.52))
    _add_area_light(
        "EvidenceKey",
        center + Vector((span * 1.8, -span * 2.0, span * 2.4)),
        target,
        1100.0,
        span * 1.5,
    )
    _add_area_light(
        "EvidenceFill",
        center + Vector((-span * 2.0, -span * 0.8, span * 1.2)),
        target,
        700.0,
        span * 1.8,
    )
    _add_area_light(
        "EvidenceRim",
        center + Vector((0.0, span * 2.0, span * 2.0)),
        target,
        900.0,
        span * 1.2,
    )

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "EvidenceCamera"
    camera.data.lens = 58.0
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.world.color = (0.035, 0.045, 0.065)

    distance = span * 2.8
    camera_height = target.z + span * 0.18
    for view_name, direction in VIEWS.items():
        camera.location = Vector(
            (
                center.x + direction.x * distance,
                center.y + direction.y * distance,
                camera_height,
            )
        )
        _aim_at(camera, target)
        scene.render.filepath = str(output_dir / f"{view_name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
