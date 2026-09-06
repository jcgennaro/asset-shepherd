"""Real-browser stale-session recovery without user tabs, credentials, or model calls."""

import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from asset_shepherd.web_evidence_renderer import find_chromium


@pytest.mark.skipif(find_chromium() is None, reason="Chromium is not installed")
@pytest.mark.parametrize(
    "scenario", ["arrival", "expiry", "restore", "action", "poll", "403", "503"]
)
def test_stale_page_goes_to_signin_without_replaying_actions(tmp_path: Path, scenario: str) -> None:
    """401 leaves the page; 403/network failures do not masquerade as an expired login."""
    script = (Path(__file__).parents[1] / "src/asset_shepherd/static/app.js").read_bytes()
    workspace = "/workspace/" + "a" * 32
    trigger = (
        "document.querySelector('button').click();" if scenario in {"action", "poll", "403"} else ""
    )
    if scenario == "restore":
        trigger = (
            "setTimeout(() => window.dispatchEvent("
            "new PageTransitionEvent('pageshow', {persisted:true})), 300);"
        )
    page = (
        '<!doctype html><body data-session-check-url="/auth/session"><div class="app-shell">'
        f'<form action="{workspace}/accept" method="post" data-busy-form data-remote-command>'
        '<button type="submit" name="decision" value="accept" data-submit-button>Use this version'
        '</button></form></div><script src="/app.js"></script><script>'
        + trigger
        + "setTimeout(() => document.body.dataset.authTest='STAY', 2500);</script></body>"
    ).encode()
    posts: list[str] = []
    redirects: list[str] = []
    fetch_headers: list[str | None] = []
    session_checks: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, body: bytes, content_type: str = "text/html") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/app.js":
                self.reply(200, script, "text/javascript")
            elif path == "/auth/login":
                redirects.append(parse_qs(urlsplit(self.path).query)["return_to"][0])
                self.reply(200, b'<body data-auth-test="PASS">Sign in</body>')
            elif path in {"/auth/session", "/receipt"}:
                fetch_headers.append(self.headers.get("X-Asset-Shepherd-Request"))
                if path == "/auth/session":
                    session_checks.append(path)
                expired = (
                    scenario == "arrival"
                    or path == "/receipt"
                    or (scenario in {"expiry", "restore"} and len(session_checks) > 1)
                )
                status = 503 if scenario == "503" else 401 if expired else 200
                seconds = 0.01 if scenario == "expiry" else 86400
                self.reply(
                    status, json.dumps({"expires_in_seconds": seconds}).encode(), "application/json"
                )
            else:
                self.reply(200, page)

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            posts.append(self.path)
            fetch_headers.append(self.headers.get("X-Asset-Shepherd-Request"))
            status = 202 if scenario == "poll" else 403 if scenario == "403" else 401
            self.reply(
                status,
                json.dumps({"status_url": "/receipt", "redirect_url": workspace}).encode(),
                "application/json",
            )

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    browser = find_chromium()
    assert browser is not None
    try:
        result = subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser'}",
                "--virtual-time-budget=4000",
                "--dump-dom",
                f"http://127.0.0.1:{server.server_port}{workspace}#current-turn",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        expected = [] if scenario in {"403", "503"} else [workspace + "#current-turn"]
        assert redirects == expected
        marker = b'data-auth-test="STAY"' if not expected else b'data-auth-test="PASS"'
        assert marker in result.stdout, result.stdout[-2500:]
        assert posts == ([workspace + "/accept"] if scenario in {"action", "poll", "403"} else [])
        assert fetch_headers and all(value == "fetch" for value in fetch_headers)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
