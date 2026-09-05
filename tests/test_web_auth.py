"""Cookie-free access, session expiry, CSRF, and OAuth callback tests without live requests."""

import base64
import json
import subprocess
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from asset_shepherd import web_auth
from asset_shepherd.web_evidence_renderer import find_chromium

VALUES = {
    "ASSET_SHEPHERD_AUTH_REQUIRED": "1",
    "ASSET_SHEPHERD_PUBLIC_ORIGIN": "https://demo.example.test",
    "ASSET_SHEPHERD_COGNITO_POOL_ID": "us-east-1_Example",
    "ASSET_SHEPHERD_COGNITO_CLIENT_ID": "exampleclient",
    "ASSET_SHEPHERD_COGNITO_DOMAIN": "https://example.auth.us-east-1.amazoncognito.com",
    "ASSET_SHEPHERD_SESSION_SECRET_ARN": (
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:example"
    ),
    "ASSET_SHEPHERD_AWS_REGION": "us-east-1",
}
TEST_KEY = "test-only-session-signer-not-a-real-credential"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Serve a gated app with a local-only signer and no secret retrieval."""

    def test_session_key(configuration: web_auth.LoginConfiguration) -> str:
        return TEST_KEY

    monkeypatch.setattr(web_auth, "load_session_key", test_session_key)
    app = FastAPI()
    web_auth.install_login(app, VALUES)

    async def protected(request: Request) -> dict[str, str]:
        return {"subject": str(request.state.login_subject)}

    app.add_api_route("/workspace", protected, methods=["GET", "POST"])
    with TestClient(
        app, base_url=VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"], follow_redirects=False
    ) as test_client:
        yield test_client


def _cookie(expires: float, *, key: str = TEST_KEY) -> str:
    payload = base64.b64encode(
        json.dumps({"subject": "invited-user", "expires_at": expires}).encode()
    )
    return TimestampSigner(key).sign(payload).decode()


def test_every_private_route_requires_login(client: TestClient) -> None:
    """Neither private downloads nor workflow actions rely on hiding a gallery link."""
    assert client.get("/workspace", headers={"accept": "text/html"}).status_code == 303
    for path in (
        "/workspace",
        "/workspace/example/model.glb",
        "/workspace/example/activity",
        "/openapi.json",
    ):
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
    assert client.post("/workspace", data={"description": "a tablet"}).status_code == 401


def test_signed_session_and_same_origin_are_both_required(client: TestClient) -> None:
    """A valid invited session can work, but expiry and cross-origin writes are rejected."""
    client.cookies.set(web_auth.SESSION_COOKIE, _cookie(time.time() + 300))
    assert client.get("/workspace").json() == {"subject": "invited-user"}
    assert client.post("/workspace").status_code == 403
    assert (
        client.post("/workspace", headers={"origin": "https://different.example.test"}).status_code
        == 403
    )
    assert (
        client.post(
            "/workspace", headers={"origin": VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"]}
        ).status_code
        == 200
    )
    client.cookies.set(web_auth.SESSION_COOKIE, _cookie(time.time() - 1))
    assert client.get("/workspace").status_code == 401
    client.cookies.set(web_auth.SESSION_COOKIE, _cookie(time.time() + 300, key="wrong-test-key"))
    assert client.get("/workspace").status_code == 401


def test_callback_requires_matching_oauth_state(client: TestClient) -> None:
    """A callback without the initiating browser session stops before token exchange."""
    response = client.get("/auth/callback?code=unused-example&state=missing")
    assert response.status_code == 401
    assert response.headers["referrer-policy"] == "no-referrer"
    assert client.get("/workspace").status_code == 401


def test_form_pages_preserve_origin_without_relaxing_csrf(client: TestClient) -> None:
    """Native forms need a non-null Origin; OAuth pages must not leak callback URLs."""
    client.cookies.set(web_auth.SESSION_COOKIE, _cookie(time.time() + 300))
    page = client.get("/workspace")
    assert page.headers["referrer-policy"] == "same-origin"
    assert page.headers["cache-control"] == "no-store"
    assert client.post("/workspace", headers={"origin": "null"}).status_code == 403
    assert client.post("/workspace").status_code == 403
    response = client.post(
        "/workspace",
        data={"action": "redo"},
        headers={"origin": VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"]},
    )
    assert response.status_code == 200
    assert client.get("/auth/signed-out").headers["referrer-policy"] == "no-referrer"


@pytest.mark.skipif(find_chromium() is None, reason="Chromium-family browser is not installed")
def test_native_browser_form_origin(client: TestClient, tmp_path: Path) -> None:
    """A fresh headless profile submits a real loopback form, never touching user tabs."""
    browser = find_chromium()
    assert browser is not None
    client.cookies.set(web_auth.SESSION_COOKIE, _cookie(time.time() + 300))
    policy = client.get("/workspace").headers["referrer-policy"]
    received: list[str | None] = []
    submitted = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Referrer-Policy", policy)
            self.end_headers()
            self.wfile.write(
                b'<form method="post" action="/redo"><button>Redo</button></form>'
                b'<script>document.querySelector("form").requestSubmit()</script>'
            )

        def do_POST(self) -> None:
            received.append(self.headers.get("Origin"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Form received")
            submitted.set()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser-profile'}",
                "--dump-dom",
                origin,
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        assert submitted.wait(2), "The native browser form did not submit"
        assert received == [origin], "Normal form submissions must not send Origin: null"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_login_uses_pkce_and_fixed_callback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual Authlib client generates browser-bound state, nonce, and S256 PKCE."""
    app = cast(FastAPI, client.app)

    async def metadata() -> dict[str, str]:
        return {
            "authorization_endpoint": VALUES["ASSET_SHEPHERD_COGNITO_DOMAIN"] + "/oauth2/authorize",
            "token_endpoint": VALUES["ASSET_SHEPHERD_COGNITO_DOMAIN"] + "/oauth2/token",
        }

    monkeypatch.setattr(app.state.login_client, "load_server_metadata", metadata)
    response = client.get("/auth/login")
    assert response.status_code == 302
    assert response.headers["referrer-policy"] == "no-referrer"
    parameters = parse_qs(urlsplit(response.headers["location"]).query)
    assert parameters["response_type"] == ["code"]
    assert parameters["redirect_uri"] == [VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"] + "/auth/callback"]
    assert parameters["code_challenge_method"] == ["S256"]
    assert len(parameters["code_challenge"][0]) == 43
    assert parameters["state"][0] and parameters["nonce"][0]


@pytest.mark.parametrize("token_seconds", [300, 86400, 172800])
def test_callback_retains_identity_but_not_tokens(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, token_seconds: int
) -> None:
    """Verified claims yield a bounded 24-hour session without retaining provider tokens."""
    now = int(time.time())
    monkeypatch.setattr(web_auth.time, "time", lambda: now)

    async def verified_token(request: Request, **kwargs: object) -> dict[str, object]:
        assert kwargs["claims_options"] == {
            "iss": {
                "essential": True,
                "value": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Example",
            }
        }
        return {
            "id_token": "not-retained",
            "refresh_token": "not-retained",
            "access_token": "not-retained",
            "userinfo": {"sub": "invited-user", "exp": now + token_seconds},
        }

    app = cast(FastAPI, client.app)
    monkeypatch.setattr(app.state.login_client, "authorize_access_token", verified_token)
    response = client.get("/auth/callback?code=unit-test")
    assert response.status_code == 303
    assert response.headers["referrer-policy"] == "no-referrer"
    cookie_header = response.headers["set-cookie"].lower()
    assert (
        "httponly" in cookie_header
        and "secure" in cookie_header
        and "samesite=lax" in cookie_header
    )
    assert "max-age=86400" in cookie_header
    assert "path=/" in cookie_header and "domain=" not in cookie_header
    value = client.cookies.get(web_auth.SESSION_COOKIE)
    assert value is not None
    session = json.loads(base64.b64decode(TimestampSigner(TEST_KEY).unsign(value)))
    assert set(session) == {"subject", "expires_at"}
    assert session["expires_at"] == now + min(token_seconds, 86400)
    assert client.get("/workspace").status_code == 200
    logout = client.post("/auth/logout", headers={"origin": VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"]})
    assert logout.status_code == 303
    assert logout.headers["location"].startswith(
        VALUES["ASSET_SHEPHERD_COGNITO_DOMAIN"] + "/logout?"
    )
    assert client.get("/workspace").status_code == 401


def test_session_lasts_24_hours_without_sliding_renewal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Activity after one hour remains valid but cannot move the fixed 24-hour boundary."""
    now = int(time.time())
    original_cookie = _cookie(now + 86400)
    client.cookies.set(web_auth.SESSION_COOKIE, original_cookie)
    for elapsed in (3601, 86399):
        monkeypatch.setattr(web_auth.time, "time", lambda elapsed=elapsed: now + elapsed)
        response = client.get("/workspace")
        assert response.status_code == 200
        # A read may leave the cookie untouched; any reissue must keep its deadline.
        value = response.cookies.get(web_auth.SESSION_COOKIE) or original_cookie
        session = json.loads(base64.b64decode(TimestampSigner(TEST_KEY).unsign(value)))
        assert session["expires_at"] == now + 86400
    monkeypatch.setattr(web_auth.time, "time", lambda: now + 86400)
    assert client.get("/workspace").status_code == 401


def test_cognito_identity_lifetime_matches_application_session() -> None:
    """The deployed ID token must not silently cap the application at the old one hour."""
    template = (Path(__file__).resolve().parents[1] / "infra/cloudformation/auth.yaml").read_text(
        encoding="utf-8"
    )
    assert "IdTokenValidity: 24" in template
    assert "IdToken: hours" in template
    assert "AccessTokenValidity: 1" in template
    assert web_auth.SESSION_SECONDS == 86400


def test_login_configuration_fails_closed() -> None:
    """Hosted login never silently turns itself off after a partial configuration failure."""
    assert web_auth.login_configuration({}) is None
    with pytest.raises(ValueError, match="incomplete"):
        web_auth.login_configuration({"ASSET_SHEPHERD_AUTH_REQUIRED": "1"})
    with pytest.raises(ValueError, match="HTTPS"):
        web_auth.login_configuration(
            {**VALUES, "ASSET_SHEPHERD_PUBLIC_ORIGIN": "http://demo.example.test"}
        )


def test_signed_out_page_is_branded_and_public(client: TestClient) -> None:
    """Signing out keeps a static mascot and a clear return path without private data."""
    response = client.get("/auth/signed-out")
    assert response.status_code == 200
    assert "Signed out — Asset Shepherd" in response.text
    assert "asset-shepherd-thinking.png" in response.text
    assert "Sign in again" in response.text
    assert 'href="/auth/login"' in response.text
    assert 'name="viewport"' in response.text
    assert "animation:" not in response.text
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
