"""Render an isolated upload-progress UI preview without uploading or invoking a model."""

import argparse
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from asset_shepherd.upload_preflight import UploadCheck
from asset_shepherd.web import HostedStartDraft, create_app
from asset_shepherd.web_evidence_renderer import find_chromium


def main() -> None:
    """Capture actual app markup and styles at desktop and narrow viewport sizes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    browser = find_chromium()
    if browser is None:
        raise RuntimeError("Chromium is required for this local UI check")
    project = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="shepherd-ui-check-") as temp:
        app = create_app(project_root=project, work_root=Path(temp) / "jobs")
        client = TestClient(app)
        templates = Jinja2Templates(directory=project / "src/asset_shepherd/templates")
        templates.env.globals["static_version"] = "preview"
        draft = HostedStartDraft("a" * 32, "Broken-heart collar.glb", Path(temp), None)

        @app.get("/preview")
        def preview(request: Request) -> Response:
            """Show the current progress cell without starting work."""
            return templates.TemplateResponse(
                request=request,
                name="hosted_upload_check.html",
                context={
                    "draft": draft,
                    "check": UploadCheck(state="CHECKING"),
                    "active_mode": "conversation",
                    "active_style": "Upload",
                    "hosted_step": "upload",
                },
            )

        class Handler(BaseHTTPRequestHandler):
            """Serve actual static assets and one inert receipt."""

            def do_GET(self) -> None:
                """Forward read-only requests into the local test app."""
                if self.path == "/frame":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b'<body style="margin:0;background:#0d1514"><iframe src="/preview" '
                        b'style="width:390px;height:844px;border:0" '
                        b'onload="document.body.dataset.overflow=String('
                        b'this.contentDocument.documentElement.scrollWidth>390)"></iframe></body>'
                    )
                    return
                if "upload-status" in self.path:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"state":"CHECKING"}')
                    return
                response = client.get(self.path, headers={"host": self.headers["Host"]})
                self.send_response(response.status_code)
                self.send_header("Content-Type", response.headers.get("content-type", "text/html"))
                self.end_headers()
                self.wfile.write(response.content)

            def log_message(self, format: str, *args: object) -> None:
                """Keep browser asset requests out of the preview output."""
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for label, width, height in (("desktop", 1280, 800), ("mobile", 1280, 900)):
                result = subprocess.run(
                    [
                        str(browser),
                        "--headless=new",
                        "--disable-gpu",
                        "--no-sandbox",
                        "--no-first-run",
                        f"--user-data-dir={Path(temp) / label}",
                        f"--window-size={width},{height}",
                        "--hide-scrollbars",
                        "--virtual-time-budget=2000",
                        "--dump-dom",
                        f"--screenshot={args.output.resolve() / (label + '.png')}",
                        f"http://127.0.0.1:{server.server_port}/"
                        + ("frame" if label == "mobile" else "preview"),
                    ],
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                if label == "mobile":
                    assert b'data-overflow="false"' in result.stdout, result.stdout[-1500:]
        finally:
            server.shutdown()
            server.server_close()
            client.close()


if __name__ == "__main__":
    main()
