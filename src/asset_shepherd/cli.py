"""Command-line interface for the deterministic Asset Shepherd core."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from asset_shepherd.inspector import inspect_asset, render_inspection_report
from asset_shepherd.models import ProjectProfile


def _write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")


def _load_profile(path: Path) -> ProjectProfile:
    return ProjectProfile.model_validate_json(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    """Build the deterministic CLI argument parser."""
    parser = argparse.ArgumentParser(prog="asset-shepherd", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="Inspect one GLB deterministically")
    inspect_parser.add_argument("source", type=Path)
    inspect_parser.add_argument("--profile", type=Path, required=True)
    inspect_parser.add_argument("--output", type=Path, required=True)
    return parser


def run_cli(arguments: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(arguments)
    try:
        profile = _load_profile(args.profile)
    except (OSError, ValidationError) as error:
        build_parser().error(f"Could not load profile: {error}")
    if args.command == "inspect":
        args.output.mkdir(parents=True, exist_ok=True)
        inspection = inspect_asset(args.source, profile)
        _write_json(args.output / "inspection.json", inspection.model_dump(mode="json"))
        (args.output / "report.md").write_text(
            render_inspection_report(inspection),
            encoding="utf-8",
            newline="\n",
        )
        return 0 if inspection.package.parse_success else 2
    return 2


def main() -> None:
    """Console-script entry point."""
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
