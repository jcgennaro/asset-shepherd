"""Import one GLB in Blender and emit reproducible machine-readable evidence.

Run with Blender, not the project Python interpreter::

    blender --background --python validation/blender/inspect_glb.py -- \
      --asset path/to/asset.glb --output path/to/blender-evidence.json
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


def _arguments() -> argparse.Namespace:
    """Parse only arguments after Blender's conventional ``--`` delimiter."""
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-blend", type=Path)
    parser.add_argument("--reexport-glb", type=Path)
    return parser.parse_args(arguments)


def _hash_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clear_scene() -> None:
    """Remove all objects from the temporary evidence scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _bounds(objects: list[Any]) -> dict[str, list[float]] | None:
    """Calculate world-space bounds over imported mesh objects."""
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points:
        return None
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return {
        "min_m": minimum,
        "max_m": maximum,
        "dimensions_m": [maximum[axis] - minimum[axis] for axis in range(3)],
    }


def _image_record(image: object) -> dict[str, object]:
    """Describe whether a Blender image has usable source data."""
    resolved = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    packed = image.packed_file is not None
    return {
        "name": image.name,
        "width": int(image.size[0]),
        "height": int(image.size[1]),
        "packed": packed,
        "source": str(image.source),
        "external_path": str(resolved) if resolved is not None else "",
        "available": packed or (resolved is not None and resolved.is_file()),
    }


def _write_json(path: Path, value: object) -> None:
    """Write stable UTF-8 JSON evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(value, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    """Import the requested GLB, collect evidence, and optionally preserve outputs."""
    args = _arguments()
    asset = args.asset.resolve(strict=True)
    output = args.output.resolve(strict=False)
    source_hash = _hash_file(asset)
    _clear_scene()
    initial_image_ids = {image.as_pointer() for image in bpy.data.images}
    started_at = datetime.now(UTC)
    import_settings = {
        "operator": "bpy.ops.import_scene.gltf",
        "filepath": str(asset),
        "default_operator_settings": True,
    }
    try:
        operator_result = sorted(bpy.ops.import_scene.gltf(filepath=str(asset)))
        objects = list(bpy.context.scene.objects)
        mesh_objects = [obj for obj in objects if obj.type == "MESH"]
        materials = sorted(
            {
                material.name
                for obj in mesh_objects
                for material in obj.data.materials
                if material is not None
            }
        )
        images = [
            _image_record(image)
            for image in bpy.data.images
            if image.as_pointer() not in initial_image_ids
        ]
        evidence: dict[str, object] = {
            "schema_version": 1,
            "generated_at": started_at.isoformat().replace("+00:00", "Z"),
            "blender_version": bpy.app.version_string,
            "asset": str(asset),
            "asset_sha256": source_hash,
            "import_success": "FINISHED" in operator_result,
            "operator_result": operator_result,
            "import_settings": import_settings,
            "scene_unit_system": bpy.context.scene.unit_settings.system,
            "scene_unit_scale_length": bpy.context.scene.unit_settings.scale_length,
            "scene_up_axis": "Z",
            "source_axis_conversion": "glTF +Y up converted by Blender importer",
            "scene_bounds": _bounds(objects),
            "object_count": len(objects),
            "mesh_object_count": len(mesh_objects),
            "vertex_count": sum(len(obj.data.vertices) for obj in mesh_objects),
            "polygon_count": sum(len(obj.data.polygons) for obj in mesh_objects),
            "material_count": len(materials),
            "materials": materials,
            "image_count": len(images),
            "images": images,
            "missing_images": [image["name"] for image in images if not image["available"]],
            "source_unchanged_verified": _hash_file(asset) == source_hash,
            "visual_anomalies": "REQUIRES_HUMAN_ADJUDICATION",
            "warnings": [],
        }
        if args.save_blend is not None:
            blend_path = args.save_blend.resolve(strict=False)
            blend_path.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
            evidence["saved_blend"] = str(blend_path)
        if args.reexport_glb is not None:
            export_path = args.reexport_glb.resolve(strict=False)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_result = sorted(
                bpy.ops.export_scene.gltf(filepath=str(export_path), export_format="GLB")
            )
            evidence["export_settings"] = {
                "operator": "bpy.ops.export_scene.gltf",
                "export_format": "GLB",
                "default_operator_settings": True,
            }
            evidence["export_result"] = export_result
            evidence["reexported_glb"] = str(export_path)
            evidence["reexported_glb_sha256"] = _hash_file(export_path)
        _write_json(output, evidence)
    except Exception as error:
        _write_json(
            output,
            {
                "schema_version": 1,
                "generated_at": started_at.isoformat().replace("+00:00", "Z"),
                "blender_version": bpy.app.version_string,
                "asset": str(asset),
                "asset_sha256": source_hash,
                "import_success": False,
                "import_settings": import_settings,
                "error_type": type(error).__name__,
                "error": str(error),
                "source_unchanged_verified": _hash_file(asset) == source_hash,
            },
        )
        raise


if __name__ == "__main__":
    main()
