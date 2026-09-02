"""Portable fixed-view GLB evidence rendering through headless Chromium."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Final, cast
from urllib.parse import urlsplit

from PIL import Image

from asset_shepherd.glb import load_glb, world_bounds


class WebEvidenceRendererError(RuntimeError):
    """Raised when the portable browser renderer cannot produce valid captures."""


_CAPTURE_NAMES: Final[tuple[str, ...]] = (
    "front.png",
    "right.png",
    "back.png",
    "left.png",
)
_CAMERA_THETA_DEGREES: Final[dict[str, float]] = {
    "front.png": 0.0,
    "right.png": -90.0,
    "back.png": 180.0,
    "left.png": 90.0,
}
_MAX_CAPTURE_BYTES: Final[int] = 32 * 1024 * 1024


@dataclass(frozen=True)
class _SceneBounds:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    @property
    def center(self) -> tuple[float, float, float]:
        return cast(
            tuple[float, float, float],
            tuple((low + high) / 2.0 for low, high in zip(self.minimum, self.maximum, strict=True)),
        )

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return cast(
            tuple[float, float, float],
            tuple(high - low for low, high in zip(self.minimum, self.maximum, strict=True)),
        )

    @property
    def longest(self) -> float:
        return max(self.dimensions)


def _asset_bounds(path: Path) -> _SceneBounds:
    measured = world_bounds(load_glb(path))
    minimum = cast(tuple[float, float, float], tuple(float(value) for value in measured.minimum))
    maximum = cast(tuple[float, float, float], tuple(float(value) for value in measured.maximum))
    if not all(math.isfinite(value) for value in (*minimum, *maximum)):
        raise WebEvidenceRendererError("GLB bounds contain non-finite values")
    bounds = _SceneBounds(minimum=minimum, maximum=maximum)
    if bounds.longest <= 1e-12:
        raise WebEvidenceRendererError("GLB bounds have no visible extent")
    return bounds


def _combined_scene(
    asset: Path, reference_asset: Path | None
) -> tuple[_SceneBounds, tuple[float, float, float] | None]:
    candidate = _asset_bounds(asset)
    if reference_asset is None:
        return candidate, None
    reference = _asset_bounds(reference_asset)
    comparison_scale = max(reference.longest, candidate.longest, 1e-6)
    offset = (
        reference.maximum[0] - candidate.minimum[0] + comparison_scale * 0.15,
        0.0,
        0.0,
    )
    shifted_minimum = (
        candidate.minimum[0] + offset[0],
        candidate.minimum[1],
        candidate.minimum[2],
    )
    shifted_maximum = (
        candidate.maximum[0] + offset[0],
        candidate.maximum[1],
        candidate.maximum[2],
    )
    combined = _SceneBounds(
        minimum=cast(
            tuple[float, float, float],
            tuple(min(reference.minimum[index], shifted_minimum[index]) for index in range(3)),
        ),
        maximum=cast(
            tuple[float, float, float],
            tuple(max(reference.maximum[index], shifted_maximum[index]) for index in range(3)),
        ),
    )
    return combined, offset


def find_chromium() -> Path | None:
    """Find a supported Chromium-family browser without requiring a Python browser SDK."""
    configured = os.environ.get("ASSET_SHEPHERD_CHROMIUM_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        return candidate if candidate.is_file() else None
    for command in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "msedge",
    ):
        discovered = shutil.which(command)
        if discovered:
            return Path(discovered)
    known_paths = (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    )
    return next((path for path in known_paths if path.is_file()), None)


class _EvidenceServer(ThreadingHTTPServer):
    """Loopback-only asset server and capture receiver for one browser run."""

    daemon_threads = True

    def __init__(
        self,
        page: bytes,
        model_viewer: Path,
        asset: Path,
        reference_asset: Path | None,
    ) -> None:
        super().__init__(("127.0.0.1", 0), _EvidenceRequestHandler)
        self.page = page
        self.model_viewer = model_viewer
        self.asset = asset
        self.reference_asset = reference_asset
        self.captures: dict[str, bytes] = {}
        self.error: str | None = None
        self.done = threading.Event()
        self.capture_lock = threading.Lock()


class _EvidenceRequestHandler(BaseHTTPRequestHandler):
    """Serve trusted local inputs and receive renderer-generated PNG bytes."""

    @property
    def evidence_server(self) -> _EvidenceServer:
        return cast(_EvidenceServer, self.server)

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _send_bytes(self, payload: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in {"/", "/renderer.html"}:
            self._send_bytes(self.evidence_server.page, "text/html; charset=utf-8")
            return
        if path == "/model-viewer.min.js":
            self._send_bytes(
                self.evidence_server.model_viewer.read_bytes(), "text/javascript; charset=utf-8"
            )
            return
        if path == "/asset.glb":
            self._send_bytes(self.evidence_server.asset.read_bytes(), "model/gltf-binary")
            return
        reference_asset = self.evidence_server.reference_asset
        if path == "/reference.glb" and reference_asset is not None:
            self._send_bytes(reference_asset.read_bytes(), "model/gltf-binary")
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > _MAX_CAPTURE_BYTES:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        payload = self.rfile.read(length)
        if path == "/error":
            with self.evidence_server.capture_lock:
                self.evidence_server.error = payload.decode("utf-8", errors="replace")[:2000]
                self.evidence_server.done.set()
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        prefix = "/capture/"
        name = path.removeprefix(prefix)
        if not path.startswith(prefix) or name not in _CAPTURE_NAMES:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        with self.evidence_server.capture_lock:
            self.evidence_server.captures[name] = payload
            if all(
                capture_name in self.evidence_server.captures for capture_name in _CAPTURE_NAMES
            ):
                self.evidence_server.done.set()
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()


def _renderer_page(
    bounds: _SceneBounds,
    candidate_offset: tuple[float, float, float] | None,
    resolution: int,
) -> bytes:
    radius = math.sqrt(sum(dimension * dimension for dimension in bounds.dimensions)) / 2.0
    field_of_view_degrees = 24.0
    # `<extra-model>` comparison staging needs a little more framing headroom than an isolated
    # model. In particular, two similarly sized assets can otherwise touch opposite image edges
    # even though the deterministic combined bounds are correct.
    framing_margin = 1.5 if candidate_offset is not None else 1.25
    camera_distance = radius / math.sin(math.radians(field_of_view_degrees / 2.0)) * framing_margin
    camera_distance = max(camera_distance, bounds.longest * 1.5, 1e-9)
    config = {
        "views": _CAMERA_THETA_DEGREES,
        "center": bounds.center,
        "cameraDistance": camera_distance,
        "fieldOfView": field_of_view_degrees,
        "comparison": candidate_offset is not None,
        "candidateOffset": candidate_offset,
    }
    extra_model = ""
    primary_source = "/asset.glb"
    if candidate_offset is not None:
        primary_source = "/reference.glb"
        offset = " ".join(f"{value:.17g}" for value in candidate_offset)
        extra_model = f'<extra-model src="/asset.glb" offset="{offset}"></extra-model>'
    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html, body {{ margin: 0; width: {resolution}px; height: {resolution}px; overflow: hidden;
      background: transparent; }}
    model-viewer {{ display: block; width: {resolution}px; height: {resolution}px;
      background-color: transparent; }}
  </style>
</head>
<body>
  <model-viewer id="viewer" src="{primary_source}" loading="eager"
    environment-image="neutral" exposure="1" shadow-intensity="0"
    interaction-prompt="none" field-of-view="{field_of_view_degrees}deg">
    {extra_model}
  </model-viewer>
  <script type="module">
    import '/model-viewer.min.js';
    const config = {json.dumps(config, separators=(",", ":"))};
    const postError = async (error) => {{
      try {{ await fetch('/error', {{method: 'POST', body: String(error)}}); }} catch (_) {{}}
    }};
    try {{
      await customElements.whenDefined('model-viewer');
      const viewer = document.getElementById('viewer');
      await new Promise((resolve, reject) => {{
        if (viewer.loaded) {{ resolve(); return; }}
        viewer.addEventListener('load', resolve, {{once: true}});
        viewer.addEventListener('error', (event) => reject(new Error(event.detail?.type ||
          'model-viewer load failed')), {{once: true}});
        setTimeout(() => reject(new Error('model-viewer load timed out')), 45000);
      }});
      if (config.comparison) await new Promise((resolve) => setTimeout(resolve, 1500));
      const target = config.center.map((value) => `${{value}}m`).join(' ');
      viewer.setAttribute('camera-target', target);
      viewer.setAttribute('field-of-view', `${{config.fieldOfView}}deg`);
      viewer.setAttribute('max-camera-orbit',
        `auto auto ${{Math.max(config.cameraDistance * 4, 1e-9)}}m`);
      for (const [name, theta] of Object.entries(config.views)) {{
        viewer.setAttribute('camera-orbit',
          `${{theta}}deg 75deg ${{config.cameraDistance}}m`);
        viewer.jumpCameraToGoal();
        await new Promise((resolve) => requestAnimationFrame(() =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await new Promise((resolve) => setTimeout(resolve, 120));
        const blob = await viewer.toBlob({{mimeType: 'image/png', idealAspect: false}});
        if (!blob) throw new Error(`capture ${{name}} returned no PNG`);
        const response = await fetch(`/capture/${{name}}`, {{method: 'POST', body: blob}});
        if (!response.ok) throw new Error(`capture upload failed: ${{response.status}}`);
      }}
    }} catch (error) {{
      await postError(error?.stack || error);
    }}
  </script>
</body>
</html>
"""
    return page.encode("utf-8")


def _write_capture(payload: bytes, output: Path, mask_output: Path) -> None:
    try:
        with Image.open(BytesIO(payload)) as opened:
            opened.load()
            rgba = opened.convert("RGBA")
    except OSError as error:
        raise WebEvidenceRendererError(
            f"Browser returned an invalid PNG for {output.name}"
        ) from error
    alpha = rgba.getchannel("A")
    alpha_extrema = cast(tuple[int, int], alpha.getextrema())
    if alpha_extrema == (255, 255):
        raise WebEvidenceRendererError(
            f"Browser capture for {output.name} did not preserve a transparent object mask"
        )
    background = Image.new("RGB", rgba.size, (7, 18, 16))
    background.paste(rgba.convert("RGB"), mask=alpha)
    background.save(output, format="PNG", optimize=True)
    alpha.save(mask_output, format="PNG", optimize=True)


def _stop_browser_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _remove_browser_profile(profile: Path) -> None:
    resolved = profile.resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if resolved.parent != temporary_root or not resolved.name.startswith("asset-shepherd-render-"):
        return
    for _attempt in range(10):
        try:
            shutil.rmtree(resolved)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(0.1)


def render_model_views(
    asset: Path,
    output_dir: Path,
    *,
    reference_asset: Path | None = None,
    resolution: int = 512,
    timeout_seconds: float = 90.0,
) -> tuple[Path, ...]:
    """Render four fixed source-axis views and matching masks through model-viewer."""
    if resolution < 128 or resolution > 2048:
        raise WebEvidenceRendererError("Render resolution must be between 128 and 2048 pixels")
    browser = find_chromium()
    if browser is None:
        raise WebEvidenceRendererError(
            "Headless Chromium is unavailable; set ASSET_SHEPHERD_CHROMIUM_PATH"
        )
    model_viewer = Path(__file__).parent / "static" / "vendor" / "model-viewer.min.js"
    if not model_viewer.is_file():
        raise WebEvidenceRendererError("Vendored model-viewer runtime is unavailable")
    bounds, candidate_offset = _combined_scene(asset, reference_asset)
    page = _renderer_page(bounds, candidate_offset, resolution)
    output_dir.mkdir(parents=True, exist_ok=True)
    server = _EvidenceServer(page, model_viewer, asset, reference_asset)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    process: subprocess.Popen[bytes] | None = None
    user_data = Path(tempfile.mkdtemp(prefix="asset-shepherd-render-"))
    try:
        url = f"http://127.0.0.1:{server.server_port}/renderer.html"
        command = [
            str(browser),
            "--headless=new",
            "--disable-background-mode",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--enable-unsafe-swiftshader",
            "--enable-webgl",
            "--force-device-scale-factor=1",
            "--hide-scrollbars",
            "--ignore-gpu-blocklist",
            "--mute-audio",
            "--no-first-run",
            f"--user-data-dir={user_data}",
            f"--window-size={resolution},{resolution}",
            url,
        ]
        if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
            command.insert(1, "--no-sandbox")
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + timeout_seconds
        while not server.done.wait(0.1):
            if process.poll() is not None:
                raise WebEvidenceRendererError(
                    f"Headless Chromium exited before rendering (exit {process.returncode})"
                )
            if time.monotonic() >= deadline:
                raise WebEvidenceRendererError("Headless Chromium rendering timed out")
        if server.error is not None:
            raise WebEvidenceRendererError(f"Headless Chromium rendering failed: {server.error}")
        paths = tuple(output_dir / name for name in _CAPTURE_NAMES)
        for name, path in zip(_CAPTURE_NAMES, paths, strict=True):
            payload = server.captures.get(name)
            if payload is None:
                raise WebEvidenceRendererError(f"Headless Chromium omitted {name}")
            _write_capture(
                payload,
                path,
                output_dir / name.replace(".png", ".mask.png"),
            )
        return paths
    finally:
        if process is not None:
            _stop_browser_process(process)
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        _remove_browser_profile(user_data)
