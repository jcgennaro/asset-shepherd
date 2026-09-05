"""Explicit fast sensor doubles for tests concerned with later workflow steps."""

from collections.abc import Callable
from pathlib import Path

import pytest

from asset_shepherd.inspector import preflight_asset
from asset_shepherd.models import PreflightResult
from asset_shepherd.upload_preflight import UploadPreflight


@pytest.fixture
def inline_upload_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep existing workflow tests synchronous; dedicated upload tests use real workers."""

    def launch(work: Callable[[], None]) -> None:
        work()

    def check(_self: UploadPreflight, source: Path) -> PreflightResult:
        return preflight_asset(source)

    monkeypatch.setattr(UploadPreflight, "_launch", staticmethod(launch))
    monkeypatch.setattr(UploadPreflight, "_check", check)
