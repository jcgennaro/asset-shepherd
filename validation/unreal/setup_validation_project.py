"""Create the isolated Unreal comparison map without importing a corpus asset."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import unreal

MAP_PATH = "/Game/Validation/AssetShepherdComparison"


def _arguments() -> argparse.Namespace:
    """Read arguments forwarded by Unreal's Python commandlet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[1:])


def _cube(
    label: str,
    location: unreal.Vector,
    scale: unreal.Vector,
) -> unreal.StaticMeshActor:
    """Spawn one labeled engine cube without project content dependencies."""
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location,
    )
    actor.set_actor_label(label)
    actor.set_actor_scale3d(scale)
    cube = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
    actor.static_mesh_component.set_static_mesh(cube)
    return actor


def main() -> None:
    """Build a fixed three-pedestal level and emit setup evidence."""
    args = _arguments()
    unreal.EditorAssetLibrary.make_directory("/Game/Validation")
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        level_subsystem.load_level(MAP_PATH)
        existing = True
    else:
        level_subsystem.new_level(MAP_PATH)
        existing = False

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.actor_has_tag("AssetShepherdScaffold"):
            actor_subsystem.destroy_actor(actor)

    positions = (-250.0, 0.0, 250.0)
    labels = ("RawPedestal", "ShepherdPedestal", "HumanReferencePedestal")
    for x_position, label in zip(positions, labels, strict=True):
        pedestal = _cube(
            label,
            unreal.Vector(x_position, 0.0, 10.0),
            unreal.Vector(1.5, 1.5, 0.2),
        )
        pedestal.tags = ["AssetShepherdScaffold"]

    scale_reference = _cube(
        "ScaleReference180cm",
        unreal.Vector(-450.0, 100.0, 90.0),
        unreal.Vector(0.1, 0.1, 1.8),
    )
    scale_reference.tags = ["AssetShepherdScaffold"]

    camera = actor_subsystem.spawn_actor_from_class(
        unreal.CameraActor,
        unreal.Vector(0.0, -900.0, 300.0),
        unreal.Rotator(-10.0, 90.0, 0.0),
    )
    camera.set_actor_label("AssetShepherdComparisonCamera")
    camera.tags = ["AssetShepherdScaffold"]

    light = actor_subsystem.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 400.0),
        unreal.Rotator(-45.0, -30.0, 0.0),
    )
    light.set_actor_label("AssetShepherdComparisonLight")
    light.tags = ["AssetShepherdScaffold"]
    level_subsystem.save_current_level()

    result = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "project": unreal.Paths.get_project_file_path(),
        "map": MAP_PATH,
        "reused_existing_map": existing,
        "pedestal_locations_cm": {
            label: [x_position, 0.0, 10.0]
            for x_position, label in zip(positions, labels, strict=True)
        },
        "scale_reference_cm": 180.0,
        "camera_label": "AssetShepherdComparisonCamera",
        "success": True,
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
