"""Acceptance for official-validator and external-render evidence adapters."""

from pathlib import Path

import pytest
from PIL import Image

from asset_shepherd.cli import run_cli
from asset_shepherd.khronos import (
    KhronosValidationResult,
    KhronosValidatorError,
    parse_khronos_report,
)
from asset_shepherd.validation.visual_compare import (
    RenderComparisonError,
    compare_render_directories,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"


def _validator_report() -> dict[str, object]:
    return {
        "uri": "clean_robot.glb",
        "validatorVersion": "2.0.0-dev.3.10",
        "issues": {
            "numErrors": 1,
            "numWarnings": 1,
            "numInfos": 0,
            "numHints": 0,
            "messages": [
                {"code": "ACCESSOR_MIN_MISMATCH", "severity": 0},
                {"code": "GENERATED_TANGENTS", "severity": 1},
            ],
        },
    }


def test_khronos_report_parser_preserves_official_counts_and_codes() -> None:
    """The official report is typed without reinterpreting validator severity."""
    result = parse_khronos_report(_validator_report())
    assert result.validator_version == "2.0.0-dev.3.10"
    assert result.error_count == result.warning_count == 1
    assert result.error_codes == ("ACCESSOR_MIN_MISMATCH",)
    assert result.error_fingerprints == ("ACCESSOR_MIN_MISMATCH||",)
    assert result.warning_codes == ("GENERATED_TANGENTS",)
    assert not result.passed


def test_khronos_report_parser_rejects_incomplete_reports() -> None:
    """Malformed external-tool output fails closed instead of becoming proof."""
    with pytest.raises(KhronosValidatorError, match="issues object"):
        parse_khronos_report({"validatorVersion": "unknown"})


def test_validate_cli_writes_typed_report_and_uses_nonzero_error_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The explicit CLI preserves official errors and returns its contracted exit code."""
    result = KhronosValidationResult.model_validate(parse_khronos_report(_validator_report()))

    def fake_validate(asset: Path, *, executable: Path | None = None) -> KhronosValidationResult:
        assert asset == CLEAN_PATH
        assert executable is None
        return result

    monkeypatch.setattr("asset_shepherd.khronos.validate_with_khronos", fake_validate)
    output = tmp_path / "official-report.json"
    exit_code = run_cli(["validate", str(CLEAN_PATH), "--output", str(output)])
    persisted = KhronosValidationResult.model_validate_json(output.read_text(encoding="utf-8"))
    assert exit_code == 5
    assert persisted == result


def test_render_comparison_emits_external_evidence_without_semantic_claim(
    tmp_path: Path,
) -> None:
    """Equal framing yields reproducible pixel metrics and an explicit evidence class."""
    reference = tmp_path / "reference"
    candidate = tmp_path / "candidate"
    reference.mkdir()
    candidate.mkdir()
    Image.new("RGBA", (2, 1), (0, 0, 0, 255)).save(reference / "front.png")
    changed = Image.new("RGBA", (2, 1), (0, 0, 0, 255))
    changed.putpixel((0, 0), (255, 0, 0, 255))
    changed.save(candidate / "front.png")

    comparison = compare_render_directories(reference, candidate, maximum_mae=32.0)

    assert comparison.interpretation == "EXTERNAL_CONSUMER_EVIDENCE"
    assert comparison.passed_configured_threshold
    assert comparison.maximum_mae_channel_units == pytest.approx(31.875)
    assert comparison.pairs[0].changed_pixel_fraction == pytest.approx(0.5)
    assert comparison.pairs[0].alpha_mae_channel_units == 0.0


def test_render_comparison_rejects_unpaired_views(tmp_path: Path) -> None:
    """Missing views cannot be silently dropped from comparison evidence."""
    reference = tmp_path / "reference"
    candidate = tmp_path / "candidate"
    reference.mkdir()
    candidate.mkdir()
    Image.new("RGB", (1, 1)).save(reference / "front.png")
    with pytest.raises(RenderComparisonError, match="Render sets differ"):
        compare_render_directories(reference, candidate)
