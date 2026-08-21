"""Command-line interface for the deterministic Asset Shepherd core."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from asset_shepherd.inspector import inspect_asset, render_inspection_report
from asset_shepherd.models import ProjectProfile
from asset_shepherd.planner import plan_repairs
from asset_shepherd.repair import apply_repairs, create_decisions


def _write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")


def _load_profile(path: Path) -> ProjectProfile:
    return ProjectProfile.model_validate_json(path.read_text(encoding="utf-8"))


def _load_approvals(path: Path) -> dict[str, bool]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Approvals must be a JSON object mapping candidate IDs to booleans")
    approvals: dict[str, bool] = {}
    for key, approved in cast(dict[object, object], value).items():
        if not isinstance(key, str) or not isinstance(approved, bool):
            raise ValueError("Every approval must map a string candidate ID to a boolean")
        approvals[key] = approved
    return approvals


def _add_job_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the deterministic CLI argument parser."""
    parser = argparse.ArgumentParser(prog="asset-shepherd", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="Inspect one GLB deterministically")
    _add_job_arguments(inspect_parser)
    plan_parser = subparsers.add_parser("plan", help="Inspect and generate repair candidates")
    _add_job_arguments(plan_parser)
    repair_parser = subparsers.add_parser("repair", help="Apply a plan with explicit approvals")
    _add_job_arguments(repair_parser)
    repair_parser.add_argument("--approvals", type=Path, required=True)
    return parser


def run_cli(arguments: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(arguments)
    try:
        profile = _load_profile(args.profile)
    except (OSError, ValidationError) as error:
        build_parser().error(f"Could not load profile: {error}")
    args.output.mkdir(parents=True, exist_ok=True)
    inspection = inspect_asset(args.source, profile)
    _write_json(args.output / "inspection.json", inspection.model_dump(mode="json"))
    (args.output / "report.md").write_text(
        render_inspection_report(inspection),
        encoding="utf-8",
        newline="\n",
    )
    if args.command == "inspect":
        return 0 if inspection.package.parse_success else 2
    plan = plan_repairs(inspection, profile)
    _write_json(args.output / "repair_plan.json", plan.model_dump(mode="json"))
    if args.command == "plan":
        return 3 if plan.blocked else 0
    if args.command == "repair":
        try:
            approvals = _load_approvals(args.approvals)
            decisions = create_decisions(
                plan,
                approvals,
                decided_at=datetime.now(UTC),
            )
            apply_repairs(
                args.source,
                args.output / "repaired.glb",
                plan,
                decisions,
            )
        except (OSError, ValueError) as error:
            build_parser().error(f"Repair failed: {error}")
        _write_json(args.output / "decisions.json", decisions.model_dump(mode="json"))
        return 0
    return 2


def main() -> None:
    """Console-script entry point."""
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
