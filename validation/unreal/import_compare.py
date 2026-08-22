"""Import raw, Shepherd, and human-reference GLBs into isolated Unreal evidence."""

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import unreal

MAP_PATH = "/Game/Validation/AssetShepherdComparison"
VARIANTS = ("raw", "shepherd", "human_reference")
LOCATIONS = {
    "raw": unreal.Vector(-250.0, 0.0, 30.0),
    "shepherd": unreal.Vector(0.0, 0.0, 30.0),
    "human_reference": unreal.Vector(250.0, 0.0, 30.0),
}


def _arguments() -> argparse.Namespace:
    """Read the three comparable inputs and evidence destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--shepherd", type=Path, required=True)
    parser.add_argument("--human-reference", type=Path, required=True)
    parser.add_argument(
        "--human-reference-role",
        default="human-cleaned reference",
        help="Provenance label for the third comparison arm",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(sys.argv[1:])


def _hash_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_call(value: object, method_name: str, *arguments: object) -> object | None:
    """Read an engine-version-dependent metric without failing a successful import."""
    method = getattr(value, method_name, None)
    if not callable(method):
        return None
    try:
        return method(*arguments)
    except Exception:
        return None


def _asset_record(asset_path: str) -> dict[str, object]:
    """Collect stable metrics exposed for an imported Unreal object."""
    asset = unreal.load_asset(asset_path)
    record: dict[str, object] = {
        "object_path": asset_path,
        "class": asset.get_class().get_name() if asset is not None else "MISSING",
    }
    if isinstance(asset, unreal.StaticMesh):
        bounds = asset.get_bounds()
        record.update(
            {
                "bounds_origin_cm": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                "bounds_extent_cm": [
                    bounds.box_extent.x,
                    bounds.box_extent.y,
                    bounds.box_extent.z,
                ],
                "material_slot_count": len(asset.get_editor_property("static_materials")),
                "vertex_count_lod0": _safe_call(asset, "get_num_vertices", 0),
                "triangle_count_lod0": _safe_call(asset, "get_num_triangles", 0),
            }
        )
    return record


def _import_variant(variant: str, source: Path, run_id: str) -> dict[str, object]:
    """Import one GLB with equal automated settings for every comparison arm."""
    destination = f"/Game/Validation/Imports/{run_id}/{variant}"
    unreal.EditorAssetLibrary.make_directory(destination)
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = destination
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = sorted(
        set(task.imported_object_paths)
        | set(
            unreal.EditorAssetLibrary.list_assets(
                destination,
                recursive=True,
                include_folder=False,
            )
        )
    )
    records = [_asset_record(path) for path in imported_paths]
    meshes = [unreal.load_asset(path) for path in imported_paths]
    meshes = [asset for asset in meshes if isinstance(asset, unreal.StaticMesh)]
    if meshes:
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            LOCATIONS[variant],
        )
        actor.static_mesh_component.set_static_mesh(meshes[0])
        actor.set_actor_label(f"AssetShepherd_{variant}")
        actor.tags = ["AssetShepherdImported"]
    return {
        "source": str(source),
        "source_sha256": _hash_file(source),
        "destination": destination,
        "import_success": bool(imported_paths),
        "run_isolated_destination": True,
        "imported_object_paths": imported_paths,
        "objects": records,
        "static_mesh_count": len(meshes),
        "texture_count": sum(record["class"].startswith("Texture") for record in records),
        "material_count": sum(record["class"].startswith("Material") for record in records),
    }


def main() -> None:
    """Run an equal-settings import comparison and write downstream evidence."""
    args = _arguments()
    sources = {
        "raw": args.raw.resolve(strict=True),
        "shepherd": args.shepherd.resolve(strict=True),
        "human_reference": args.human_reference.resolve(strict=True),
    }
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if re.fullmatch(r"[A-Za-z0-9_]+", run_id) is None:
        raise ValueError("--run-id may contain only ASCII letters, digits, and underscores")
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError("Run setup_validation_project.py before comparison import")
    level_subsystem.load_level(MAP_PATH)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.actor_has_tag("AssetShepherdImported"):
            actor_subsystem.destroy_actor(actor)
    comparisons = {
        variant: _import_variant(variant, sources[variant], run_id) for variant in VARIANTS
    }
    level_subsystem.save_current_level()
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "map": MAP_PATH,
        "run_id": run_id,
        "equivalent_import_settings": {
            "automated": True,
            "replace_existing": True,
            "replace_existing_settings": True,
            "save": True,
        },
        "comparison_arm_roles": {
            "raw": "untouched source export",
            "shepherd": "Asset Shepherd repaired candidate",
            "human_reference": args.human_reference_role,
        },
        "comparisons": comparisons,
        "commandlet_log_directory": unreal.Paths.project_log_dir(),
        "warning_error_evidence": "Preserve and review the commandlet log with this record",
        "visual_anomalies": "REQUIRES_HUMAN_ADJUDICATION",
        "standardized_screenshots": "REQUIRES_EDITOR_CAPTURE",
    }
    output = args.output.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"{json.dumps(result, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
