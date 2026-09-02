"""Acceptance checks for portable browser-rendered model evidence."""

from pathlib import Path

import pytest
from PIL import Image

from asset_shepherd.web_evidence_renderer import find_chromium, render_model_views

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_find_chromium_honors_explicit_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit browser path takes precedence over platform discovery."""
    browser = tmp_path / "chromium"
    browser.write_bytes(b"placeholder")
    monkeypatch.setenv("ASSET_SHEPHERD_CHROMIUM_PATH", str(browser))

    assert find_chromium() == browser


@pytest.mark.skipif(find_chromium() is None, reason="Chromium-family browser is not installed")
def test_web_renderer_produces_four_pngs_and_object_masks(tmp_path: Path) -> None:
    """A real local browser produces the complete fixed-view evidence inventory."""
    paths = render_model_views(
        PROJECT_ROOT / "fixtures" / "clean_robot.glb",
        tmp_path,
        timeout_seconds=60,
    )

    assert tuple(path.name for path in paths) == (
        "front.png",
        "right.png",
        "back.png",
        "left.png",
    )
    for path in paths:
        mask_path = path.with_name(path.name.replace(".png", ".mask.png"))
        with Image.open(path) as rendered:
            assert rendered.format == "PNG"
            assert rendered.size == (512, 512)
        with Image.open(mask_path) as mask:
            assert mask.format == "PNG"
            assert mask.mode == "L"
            assert mask.getextrema() == (0, 255)
