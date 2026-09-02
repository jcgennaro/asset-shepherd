"""Aggregate bounded live-provider runs into one hash-bound release gate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from asset_shepherd.provider_acceptance import (
    aggregate_acceptance_summaries,
    load_acceptance_manifest,
    write_json,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("validation/provider-acceptance/cases.json"),
    )
    parser.add_argument("--input-root", type=Path, default=Path("build/provider-acceptance"))
    parser.add_argument("--output-root", type=Path, default=Path("build/provider-acceptance"))
    return parser.parse_args()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80]


def _load_mapping(path: Path) -> dict[str, object] | None:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    raw_mapping = cast(dict[object, object], decoded)
    return {key: value for key, value in raw_mapping.items() if isinstance(key, str)}


def main() -> int:
    """Write one aggregate without copying mutable asset payloads."""
    args = _arguments()
    repository_root = Path(__file__).resolve().parents[1]
    manifest = load_acceptance_manifest((repository_root / args.manifest).resolve(strict=True))
    input_root = (repository_root / args.input_root).resolve(strict=True)
    summaries: list[tuple[str, dict[str, object]]] = []
    for run_root in sorted(path for path in input_root.iterdir() if path.is_dir()):
        if "-aggregate-" in run_root.name:
            continue
        records = [
            record
            for result_path in sorted(run_root.glob("*/acceptance_result.json"))
            if (record := _load_mapping(result_path)) is not None
        ]
        if records:
            summaries.append(
                (
                    run_root.name,
                    {
                        "provider": records[0].get("provider"),
                        "model_id": records[0].get("model_id"),
                        "case_results": records,
                    },
                )
            )
            continue
        summary = _load_mapping(run_root / "run_summary.json")
        if summary is not None:
            summaries.append((run_root.name, summary))

    aggregate = aggregate_acceptance_summaries(
        manifest,
        summaries,
        provider=args.provider,
        model_id=args.model_id,
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"{timestamp}-aggregate-{_slug(args.provider)}-{_slug(args.model_id)}"
    aggregate["run_name"] = run_name
    output_root = (repository_root / args.output_root / run_name).resolve(strict=False)
    if output_root.exists():
        raise SystemExit(f"Refusing to overwrite aggregate: {output_root}")
    write_json(output_root / "run_summary.json", aggregate)
    print(json.dumps({**aggregate, "case_results": None}, sort_keys=True), flush=True)
    return 0 if aggregate["release_gate"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
