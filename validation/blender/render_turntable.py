"""Render four neutral evidence views of one GLB in Blender background mode."""

import argparse
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

VIEWS = {
    # Blender imports glTF (X, Y, Z) as (X, -Z, Y). These camera positions therefore
    # correspond to source +Z (front), -X (right), -Z (back), and +X (left).
    "front": Vector((0.0, -1.0, 0.0)),
    "right": Vector((-1.0, 0.0, 0.0)),
    "back": Vector((0.0, 1.0, 0.0)),
    "left": Vector((1.0, 0.0, 0.0)),
}


def _arguments() -> argparse.Namespace:
    """Parse arguments after Blender's conventional ``--`` delimiter."""
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument(
        "--reference-asset",
        type=Path,
        help="Optional source GLB to stage beside --asset at unchanged relative scale.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(arguments)


def _clear_scene() -> None:
    """Clear the temporary evidence scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _mesh_bound_points(objects: list[Any]) -> list[Vector]:
    """Return every imported mesh object's world-space bounding-box corner."""
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points:
        raise ValueError("Imported GLB contains no mesh bounds to render")
    return points


def _mesh_bounds(objects: list[Any]) -> tuple[Vector, Vector]:
    """Return world-space minimum and maximum corners for imported meshes."""
    points = _mesh_bound_points(objects)
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return minimum, maximum


def _import_asset(path: Path) -> list[Any]:
    """Import one GLB and return only the objects created by that import."""
    existing = set(bpy.context.scene.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender GLB import failed: {sorted(result)}")
    return [obj for obj in bpy.context.scene.objects if obj not in existing]


def _translate_import(objects: list[Any], offset: Vector) -> None:
    """Translate one imported hierarchy exactly once through its top-level objects."""
    imported = set(objects)
    for obj in objects:
        if obj.parent not in imported:
            obj.location += offset


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
    reference_asset = (
        args.reference_asset.resolve(strict=True) if args.reference_asset is not None else None
    )
    output_dir = args.output_dir.resolve(strict=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_scene()
    if reference_asset is None:
        objects = _import_asset(asset)
    else:
        reference_objects = _import_asset(reference_asset)
        reference_minimum, reference_maximum = _mesh_bounds(reference_objects)
        candidate_objects = _import_asset(asset)
        candidate_minimum, candidate_maximum = _mesh_bounds(candidate_objects)
        reference_span = max(reference_maximum - reference_minimum)
        candidate_span = max(candidate_maximum - candidate_minimum)
        gap = max(reference_span, candidate_span, 1e-6) * 0.15
        _translate_import(
            candidate_objects,
            Vector((reference_maximum.x - candidate_minimum.x + gap, 0.0, 0.0)),
        )
        objects = reference_objects + candidate_objects
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
    # Blender area-light power is measured in watts. Scale it with the square of the
    # framed asset span so physically equivalent assets at different represented sizes
    # receive equivalent illumination from this proportional camera/light rig.
    light_power_scale = span * span
    _add_area_light(
        "EvidenceKey",
        center + Vector((span * 1.8, -span * 2.0, span * 2.4)),
        target,
        1100.0 * light_power_scale,
        span * 1.5,
    )
    _add_area_light(
        "EvidenceFill",
        center + Vector((-span * 2.0, -span * 0.8, span * 1.2)),
        target,
        700.0 * light_power_scale,
        span * 1.8,
    )
    _add_area_light(
        "EvidenceRim",
        center + Vector((0.0, span * 2.0, span * 2.0)),
        target,
        900.0 * light_power_scale,
        span * 1.2,
    )

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "EvidenceCamera"
    # Orthographic evidence removes perspective as a confounder and lets each source-axis
    # projection use its own framing. A single longest-axis perspective distance makes the side
    # of a long, thin asset occupy only a few pixels even though the asset is valid and present.
    camera.data.type = "ORTHO"
    # Blender defaults to a 10 cm near plane. That clips tiny but valid candidates when the
    # proportional camera rig moves inside 10 cm, producing a misleading blank render.
    camera.data.clip_start = max(span * 0.001, 1e-7)
    camera.data.clip_end = max(span * 100.0, camera.data.clip_start * 1000.0)
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

    mask_material = bpy.data.materials.new("EvidenceMaskMaterial")
    mask_material.use_nodes = True
    mask_nodes = mask_material.node_tree.nodes
    mask_nodes.clear()
    mask_output = mask_nodes.new("ShaderNodeOutputMaterial")
    mask_emission = mask_nodes.new("ShaderNodeEmission")
    mask_emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    mask_emission.inputs["Strength"].default_value = 1.0
    mask_material.node_tree.links.new(
        mask_emission.outputs["Emission"], mask_output.inputs["Surface"]
    )

    # Leave deterministic depth room around the import. The orthographic scale below is fitted
    # independently to the visible projection; a source/candidate comparison is still one import
    # and therefore receives one shared scale for each corresponding view.
    distance = span * 3.8
    camera_height = target.z + span * 0.18
    bound_points = _mesh_bound_points(objects)
    for view_name, direction in VIEWS.items():
        camera.location = Vector(
            (
                center.x + direction.x * distance,
                center.y + direction.y * distance,
                camera_height,
            )
        )
        _aim_at(camera, target)
        bpy.context.view_layer.update()
        camera_inverse = camera.matrix_world.inverted()
        camera_points = [camera_inverse @ point for point in bound_points]
        projected_width = max(point.x for point in camera_points) - min(
            point.x for point in camera_points
        )
        projected_height = max(point.y for point in camera_points) - min(
            point.y for point in camera_points
        )
        camera.data.ortho_scale = max(projected_width, projected_height, span * 1e-6) * 1.35
        scene.render.filepath = str(output_dir / f"{view_name}.png")
        bpy.ops.render.render(write_still=True)
        scene.view_layers[0].material_override = mask_material
        ground.hide_render = True
        previous_world_color = tuple(scene.world.color)
        scene.world.color = (0.0, 0.0, 0.0)
        scene.render.filepath = str(output_dir / f"{view_name}.mask.png")
        bpy.ops.render.render(write_still=True)
        scene.world.color = previous_world_color
        ground.hide_render = False
        scene.view_layers[0].material_override = None


if __name__ == "__main__":
    main()
