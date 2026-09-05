"""Cookie-free access, session expiry, CSRF, and OAuth callback tests without live requests."""

import base64
import json
import time
from collections.abc import Iterator
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from asset_shepherd import web_auth

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
    assert client.get("/workspace").status_code == 401


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
    parameters = parse_qs(urlsplit(response.headers["location"]).query)
    assert parameters["response_type"] == ["code"]
    assert parameters["redirect_uri"] == [VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"] + "/auth/callback"]
    assert parameters["code_challenge_method"] == ["S256"]
    assert len(parameters["code_challenge"][0]) == 43
    assert parameters["state"][0] and parameters["nonce"][0]


def test_callback_retains_identity_but_not_tokens(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authlib-verified claims yield a short session without storing OIDC tokens in cookies."""

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
            "userinfo": {"sub": "invited-user", "exp": int(time.time()) + 300},
        }

    app = cast(FastAPI, client.app)
    monkeypatch.setattr(app.state.login_client, "authorize_access_token", verified_token)
    response = client.get("/auth/callback?code=unit-test")
    assert response.status_code == 303
    cookie_header = response.headers["set-cookie"].lower()
    assert (
        "httponly" in cookie_header
        and "secure" in cookie_header
        and "samesite=lax" in cookie_header
    )
    value = client.cookies.get(web_auth.SESSION_COOKIE)
    assert value is not None
    session = json.loads(base64.b64decode(TimestampSigner(TEST_KEY).unsign(value)))
    assert set(session) == {"subject", "expires_at"}
    assert client.get("/workspace").status_code == 200
    logout = client.post("/auth/logout", headers={"origin": VALUES["ASSET_SHEPHERD_PUBLIC_ORIGIN"]})
    assert logout.status_code == 303
    assert logout.headers["location"].startswith(
        VALUES["ASSET_SHEPHERD_COGNITO_DOMAIN"] + "/logout?"
    )
    assert client.get("/workspace").status_code == 401


def test_login_configuration_fails_closed() -> None:
    """Hosted login never silently turns itself off after a partial configuration failure."""
    assert web_auth.login_configuration({}) is None
    with pytest.raises(ValueError, match="incomplete"):
        web_auth.login_configuration({"ASSET_SHEPHERD_AUTH_REQUIRED": "1"})
    with pytest.raises(ValueError, match="HTTPS"):
        web_auth.login_configuration(
            {**VALUES, "ASSET_SHEPHERD_PUBLIC_ORIGIN": "http://demo.example.test"}
        )
