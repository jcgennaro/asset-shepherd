"""Generate parseable GLBs with deterministic geometry defects."""

from pathlib import Path

from asset_shepherd.fixtures import generate_geometry_failure_fixtures

PROJECT_ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    generated = generate_geometry_failure_fixtures(
        PROJECT_ROOT / "fixtures" / "clean_robot.glb",
        PROJECT_ROOT / "fixtures" / "geometry_failures",
    )
    for generated_path in generated:
        print(generated_path.relative_to(PROJECT_ROOT))
