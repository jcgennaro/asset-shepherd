"""Compare equally framed consumer renders and emit typed pixel-distance evidence."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from asset_shepherd.validation.models import RenderComparison, RenderPairMetrics


class RenderComparisonError(ValueError):
    """Raised when two render sets cannot be compared without guessing."""


def _png_map(directory: Path) -> dict[str, Path]:
    resolved = directory.resolve(strict=True)
    if not resolved.is_dir():
        raise RenderComparisonError(f"Render path is not a directory: {directory}")
    return {
        path.relative_to(resolved).as_posix(): path
        for path in resolved.rglob("*.png")
        if path.is_file()
    }


def _pair_metrics(name: str, reference: Path, candidate: Path) -> RenderPairMetrics:
    with Image.open(reference) as reference_image:
        reference_rgba = np.asarray(reference_image.convert("RGBA"), dtype=np.float64)
    with Image.open(candidate) as candidate_image:
        candidate_rgba = np.asarray(candidate_image.convert("RGBA"), dtype=np.float64)
    if reference_rgba.shape != candidate_rgba.shape:
        raise RenderComparisonError(
            f"Render dimensions differ for {name}: "
            f"{reference_rgba.shape[:2]} != {candidate_rgba.shape[:2]}"
        )
    absolute = np.abs(reference_rgba - candidate_rgba)
    squared = np.square(reference_rgba - candidate_rgba)
    changed_pixels = np.any(absolute > 0.0, axis=2)
    height, width, _ = reference_rgba.shape
    return RenderPairMetrics(
        name=name,
        width=width,
        height=height,
        mae_channel_units=float(np.mean(absolute)),
        rmse_channel_units=float(np.sqrt(np.mean(squared))),
        maximum_channel_delta=float(np.max(absolute)),
        alpha_mae_channel_units=float(np.mean(absolute[:, :, 3])),
        changed_pixel_fraction=float(np.mean(changed_pixels)),
    )


def compare_render_directories(
    reference_directory: Path,
    candidate_directory: Path,
    *,
    maximum_mae: float | None = None,
) -> RenderComparison:
    """Compare identically named PNG sets without making a semantic visual judgment."""
    if maximum_mae is not None and maximum_mae < 0.0:
        raise RenderComparisonError("Maximum MAE must be non-negative")
    reference = _png_map(reference_directory)
    candidate = _png_map(candidate_directory)
    if not reference:
        raise RenderComparisonError("Reference directory contains no PNG renders")
    if reference.keys() != candidate.keys():
        missing = sorted(reference.keys() - candidate.keys())
        unexpected = sorted(candidate.keys() - reference.keys())
        raise RenderComparisonError(
            f"Render sets differ; missing={missing}, unexpected={unexpected}"
        )
    pairs = tuple(
        _pair_metrics(name, reference[name], candidate[name]) for name in sorted(reference)
    )
    observed_maximum = max(pair.mae_channel_units for pair in pairs)
    return RenderComparison(
        reference_directory=str(reference_directory.resolve()),
        candidate_directory=str(candidate_directory.resolve()),
        threshold_mae_channel_units=maximum_mae,
        pairs=pairs,
        maximum_mae_channel_units=observed_maximum,
        passed_configured_threshold=(
            None if maximum_mae is None else observed_maximum <= maximum_mae
        ),
    )


def main() -> None:
    """Run the deterministic render comparison CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-mae", type=float)
    args = parser.parse_args()
    try:
        result = compare_render_directories(
            args.reference,
            args.candidate,
            maximum_mae=args.maximum_mae,
        )
    except (OSError, RenderComparisonError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"{result.model_dump_json(indent=2)}\n",
        encoding="utf-8",
        newline="\n",
    )
    if result.passed_configured_threshold is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
