"""Bounded, model-free upload checks outside the HTTP request lifetime."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from threading import RLock, Thread
from time import monotonic
from typing import Literal

from pydantic import BaseModel

from asset_shepherd.models import PreflightResult, RepairEligibility


class UploadCheck(BaseModel):
    """Persisted receipt, never an authorization to repair an asset."""

    state: Literal["CHECKING", "READY", "FAILED"]
    error: str | None = None
    preflight: PreflightResult | None = None


class UploadPreflight:
    """Run one isolated, time-bounded geometry check at a time per web process."""

    def __init__(self, timeout_seconds: float = 240) -> None:
        """Keep the existing small web tier responsive without an unbounded work queue."""
        self.timeout_seconds = timeout_seconds
        self._lock = RLock()
        self._active: set[Path] = set()

    @staticmethod
    def _write(root: Path, check: UploadCheck) -> None:
        path = root / "upload-check.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(check.model_dump_json(), encoding="utf-8")
        temporary.replace(path)

    def reuse(self, root: Path, preflight: PreflightResult) -> None:
        """Store prior source-bound evidence; workspace creation checks the hash again."""
        self._write(root, UploadCheck(state="READY", preflight=preflight))

    def status(self, root: Path) -> UploadCheck | None:
        """Restore terminal results, but fail interrupted work rather than spin forever."""
        with self._lock:
            path = root / "upload-check.json"
            if not path.is_file():
                return None
            check = UploadCheck.model_validate_json(path.read_text(encoding="utf-8"))
            if check.state == "CHECKING" and root not in self._active:
                check = UploadCheck(
                    state="FAILED",
                    error="Asset checking was interrupted. Check the uploaded file again.",
                )
                self._write(root, check)
            return check

    def start(self, root: Path, on_ready: Callable[[], None] | None = None) -> None:
        """Return immediately; reject concurrent heavy checks instead of exhausting memory."""
        with self._lock:
            if root in self._active:
                return
            if self._active:
                raise ValueError("Another upload is being checked. Please wait, then try again.")
            self._active.add(root)
            try:
                self._write(root, UploadCheck(state="CHECKING"))
                self._launch(lambda: self._run(root, on_ready))
            except Exception:
                self._active.discard(root)
                raise

    @staticmethod
    def _launch(work: Callable[[], None]) -> None:
        Thread(target=work, name="upload-preflight", daemon=True).start()

    def _check(self, source: Path) -> PreflightResult:
        # No shell, user-selected executable, provider request, or asset-supplied code.
        env = dict(os.environ)
        env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        result = subprocess.run(
            [sys.executable, "-m", "asset_shepherd.upload_preflight", str(source)],
            capture_output=True,
            check=True,
            timeout=self.timeout_seconds,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return PreflightResult.model_validate_json(result.stdout)

    def _run(self, root: Path, on_ready: Callable[[], None] | None) -> None:
        started = monotonic()
        try:
            preflight = self._check(root / "source.glb")
            if not preflight.package.parse_success:
                check = UploadCheck(
                    state="FAILED", error="This GLB is damaged or incomplete and could not be read."
                )
            elif preflight.structural_eligibility is RepairEligibility.INVALID_OR_UNREADABLE:
                check = UploadCheck(state="FAILED", error=preflight.parse_error)
            else:
                check = UploadCheck(state="READY", preflight=preflight)
                if on_ready is not None:
                    on_ready()
        except subprocess.TimeoutExpired:
            check = UploadCheck(
                state="FAILED",
                error="Checking this asset exceeded four minutes. No model was called. "
                "You can retry checking or choose a less complex export.",
            )
        except Exception:
            # Do not expose subprocess output, credentials, or parser internals to the browser.
            check = UploadCheck(
                state="FAILED",
                error="Asset checking could not finish. No model was called. "
                "Try checking the uploaded file again or choose another GLB.",
            )
        with self._lock:
            try:
                self._write(root, check)
            finally:
                self._active.discard(root)
        logging.getLogger(__name__).info(
            "Upload preflight %s: %s in %.2fs", root.name, check.state, monotonic() - started
        )


if __name__ == "__main__":
    from asset_shepherd.inspector import preflight_asset

    sys.stdout.buffer.write(preflight_asset(Path(sys.argv[1])).model_dump_json().encode("utf-8"))
