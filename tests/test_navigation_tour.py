"""First-visit navigation help, not workflow automation or model evaluation."""

import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from asset_shepherd.web import create_app
from asset_shepherd.web_evidence_renderer import find_chromium

ROOT = Path(__file__).resolve().parents[1]


def test_tour_entry_points_and_no_autostart_during_upload(tmp_path: Path) -> None:
    """Gallery offers first-visit help; working pages never interrupt an active task."""
    client = TestClient(create_app(project_root=ROOT, work_root=tmp_path / "jobs"))
    assert "data-tour-auto" in client.get("/workspace").text
    upload = client.get("/workspace/new/upload").text
    assert "data-navigation-tour" not in upload
    assert "data-tour-auto" not in upload
    faq = client.get("/faq").text
    assert "Replay navigation tour" in faq
    assert "data-navigation-tour-open" in faq


@pytest.mark.skipif(find_chromium() is None, reason="Chromium is not installed")
@pytest.mark.parametrize("finish", ["complete", "skip", "storage-disabled"])
def test_navigation_tour_in_real_browser(tmp_path: Path, finish: str) -> None:
    """Exercise real markup/JS, next/back, dismissal, remembered visits, and FAQ replay."""
    client = TestClient(create_app(project_root=ROOT, work_root=tmp_path / "jobs"))
    requests: list[str] = []
    script = """
    <script>
    window.addEventListener('load', () => {
      const dialog = document.querySelector('[data-navigation-tour]');
      const get = (name) => dialog.querySelector('[data-tour-' + name + ']');
      function require(value, message) { if (!value) throw new Error(message); }
      try {
        const phase = new URLSearchParams(location.search).get('phase');
        if (phase === 'revisit') {
          require(!dialog.open, 'tour repeated on a remembered visit');
          location.replace('/faq?phase=replay'); return;
        }
        if (phase === 'replay') {
          const button = document.querySelector('[data-navigation-tour-open]');
          button.closest('details').open = true;
          button.focus(); button.click();
          require(dialog.open, 'FAQ replay failed');
          get('skip').click();
          setTimeout(() => {
            const restored = !dialog.open && document.activeElement === button;
            document.body.dataset.tourTest = restored ? 'PASS' : 'FAIL';
          }, 50); return;
        }
        require(dialog.open, 'first visit did not open tour');
        require(get('back').disabled, 'back enabled on first step');
        get('next').click(); require(get('count').textContent === '2 of 4', 'next failed');
        get('back').click(); require(get('count').textContent === '1 of 4', 'back failed');
        if (FINISH === 'complete') {
          get('next').click(); get('next').click(); get('next').click();
          require(get('next').textContent === 'Got it', 'last button is unclear');
          get('next').click();
        } else { get('skip').click(); }
        setTimeout(() => {
          if (dialog.open) { document.body.dataset.tourTest = 'FAIL'; return; }
          if (FINISH === 'storage-disabled') document.body.dataset.tourTest = 'PASS';
          else location.replace('/workspace?phase=revisit');
        }, 50);
      } catch (error) { document.body.dataset.tourTest = 'FAIL: ' + error.message; }
    });
    </script>
    """.replace("FINISH", repr(finish))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            response = client.get(self.path, headers={"host": self.headers["Host"]})
            content = response.content
            if "text/html" in response.headers.get("content-type", ""):
                if finish == "storage-disabled":
                    content = content.replace(
                        b"<head>",
                        b"<head><script>for(const key of ['localStorage','sessionStorage'])"
                        b"Object.defineProperty(window,key,"
                        b"{get(){throw Error('Storage disabled')}})"
                        b"</script>",
                    )
                content = content.replace(b"</body>", script.encode() + b"</body>")
            self.send_response(response.status_code)
            self.send_header("Content-Type", response.headers.get("content-type", "text/html"))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:
            requests.append("UNEXPECTED POST")
            self.send_error(405)

        def log_message(self, format: str, *args: object) -> None:
            pass

    browser = find_chromium()
    assert browser is not None
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser'}",
                "--virtual-time-budget=5000",
                "--dump-dom",
                f"http://127.0.0.1:{server.server_port}/workspace",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        assert b'data-tour-test="PASS"' in result.stdout, result.stdout[-5000:]
        assert "UNEXPECTED POST" not in requests
    finally:
        server.shutdown()
        server.server_close()
        client.close()
