"""Exercise remote form serialization in Chromium without models or cloud mutations."""

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import FastAPI, Form
from fastapi.testclient import TestClient

from asset_shepherd.web_evidence_renderer import find_chromium


@pytest.mark.skipif(find_chromium() is None, reason="Chromium-family browser is not installed")
@pytest.mark.parametrize("decision", ["approve", "reject", "revise", "accept"])
def test_remote_form_includes_exact_decision(decision: str, tmp_path: Path) -> None:
    """Actual app.js must retain the clicked decision and externally associated fields."""
    app = FastAPI()

    def receive(
        decision: Annotated[str, Form()],
        interrupt_id: Annotated[str, Form()],
        command_id: Annotated[str, Form()],
        response_size_and_pose: Annotated[str, Form()],
    ) -> dict[str, str]:
        return {
            "decision": decision,
            "interrupt_id": interrupt_id,
            "command_id": command_id,
            "response_size_and_pose": response_size_and_pose,
        }

    app.add_api_route("/decision", receive, methods=["POST"], status_code=202)
    script = (Path(__file__).parents[1] / "src/asset_shepherd/static/app.js").read_bytes()
    button = (
        '<input type="hidden" name="decision" value="accept">'
        '<button type="submit">Use this version</button>'
        if decision == "accept"
        else f'<button type="submit" name="decision" value="{decision}" '
        "data-submit-button>Send</button>"
    )
    page = (
        '<form id="response" action="/decision" method="post" data-busy-form data-remote-command>'
        '<input type="hidden" name="interrupt_id" value="test-interrupt">'
        '<input type="hidden" name="command_id" value="test-command">'
        f'{button}</form><select name="response_size_and_pose" form="response">'
        '<option value="accept">Accept</option></select><script src="/app.js"></script>'
        '<script>document.querySelector("button").click()</script>'
    ).encode()
    received: list[tuple[int, object]] = []
    submitted = threading.Event()
    client = TestClient(app)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            data = script if self.path == "/app.js" else page
            if self.path == "/receipt":
                data = b'{"state":"FAILED","error":"Test complete; no action executed."}'
            self.send_response(200)
            self.send_header(
                "Content-Type", "text/javascript" if self.path == "/app.js" else "text/html"
            )
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            result = client.post(
                "/decision", content=body, headers={"Content-Type": self.headers["Content-Type"]}
            )
            received.append((result.status_code, result.json()))
            self.send_response(result.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status_url": "/receipt", "redirect_url": "/"}).encode())
            submitted.set()

        def log_message(self, format: str, *args: object) -> None:
            pass

    browser = find_chromium()
    assert browser is not None
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser-profile'}",
                "--virtual-time-budget=2000",
                "--dump-dom",
                f"http://127.0.0.1:{server.server_port}",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        assert submitted.wait(2), "The remote form never reached the fixture endpoint"
        assert received == [
            (
                202,
                {
                    "decision": decision,
                    "interrupt_id": "test-interrupt",
                    "command_id": "test-command",
                    "response_size_and_pose": "accept",
                },
            )
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        client.close()
