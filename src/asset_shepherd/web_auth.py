"""Invite-only Cognito login gate for the shared hosted demo, not tenant isolation."""

# Authlib's Starlette integration exposes dynamic OAuth registration and token dictionaries.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedFunction=false

import json
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlencode, urlsplit

import boto3
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp

SESSION_COOKIE = "__Host-asset-shepherd-session"
SESSION_SECONDS = 3600


@dataclass(frozen=True)
class LoginConfiguration:
    """Deployment-owned endpoints and secret reference; no browser-selected destinations."""

    origin: str
    issuer: str
    domain: str
    client_id: str
    secret_arn: str
    region: str


def login_configuration(values: Mapping[str, str]) -> LoginConfiguration | None:
    """Allow the local offline mode, but fail closed on incomplete hosted login settings."""
    names = (
        "ASSET_SHEPHERD_PUBLIC_ORIGIN",
        "ASSET_SHEPHERD_COGNITO_POOL_ID",
        "ASSET_SHEPHERD_COGNITO_DOMAIN",
        "ASSET_SHEPHERD_COGNITO_CLIENT_ID",
        "ASSET_SHEPHERD_SESSION_SECRET_ARN",
    )
    required = values.get("ASSET_SHEPHERD_AUTH_REQUIRED", "0")
    if required not in {"0", "1"}:
        raise ValueError("ASSET_SHEPHERD_AUTH_REQUIRED must be 0 or 1")
    configured = [values.get(name, "").strip() for name in names]
    if required == "0" and not any(configured):
        return None
    if not all(configured):
        raise ValueError("Hosted login configuration is incomplete; refusing to start")
    origin, pool_id, domain, client_id, secret_arn = configured
    region = values.get("ASSET_SHEPHERD_AWS_REGION", "").strip()
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Hosted login requires one canonical HTTPS origin")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", region):
        raise ValueError("Hosted login requires an AWS region")
    if not re.fullmatch(re.escape(region) + r"_[A-Za-z0-9]+", pool_id):
        raise ValueError("Cognito pool must belong to the configured region")
    if not re.fullmatch(
        r"https://[a-z0-9-]+\.auth\." + re.escape(region) + r"\.amazoncognito\.com", domain
    ):
        raise ValueError("Cognito login domain is invalid")
    if not re.fullmatch(r"[a-z0-9]+", client_id):
        raise ValueError("Cognito client ID is invalid")
    if not re.fullmatch(
        r"arn:aws:secretsmanager:" + re.escape(region) + r":\d{12}:secret:[A-Za-z0-9/_+=.@-]+",
        secret_arn,
    ):
        raise ValueError("Session signing key must reference one Secrets Manager ARN")
    return LoginConfiguration(
        origin.rstrip("/"),
        f"https://cognito-idp.{region}.amazonaws.com/{pool_id}",
        domain,
        client_id,
        secret_arn,
        region,
    )


def load_session_key(configuration: LoginConfiguration) -> str:
    """Retrieve only the session signer into server memory; never log the secret response."""
    client = boto3.Session(region_name=configuration.region).client("secretsmanager")
    response = client.get_secret_value(SecretId=configuration.secret_arn)
    payload = json.loads(cast(str, response["SecretString"]))
    key = payload.get("session_key")
    if not isinstance(key, str) or len(key) < 32:
        raise ValueError("Session signing secret is invalid; refusing to start")
    return key


class LoginGate(BaseHTTPMiddleware):
    """Authenticate all data/action routes and reject cross-origin authenticated writes."""

    def __init__(self, app: ASGIApp, *, origin: str) -> None:
        """Bind CSRF checks to the trusted configured origin, never the Host header."""
        super().__init__(app)
        self.origin = origin

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Leave only static assets, OAuth entry/callback, and health publicly readable."""
        public = request.url.path in {
            "/healthz",
            "/auth/login",
            "/auth/callback",
            "/auth/signed-out",
        } or request.url.path.startswith("/static/")
        if not public:
            subject = request.session.get("subject")
            expires = request.session.get("expires_at", 0)
            valid = (
                isinstance(subject, str)
                and bool(subject)
                and isinstance(expires, (int, float))
                and expires > time.time()
            )
            if not valid:
                request.session.clear()
                if request.method in {"GET", "HEAD"} and "text/html" in request.headers.get(
                    "accept", ""
                ):
                    return RedirectResponse(
                        "/auth/login", status_code=303, headers={"Cache-Control": "no-store"}
                    )
                return JSONResponse(
                    {"detail": "Sign in required"},
                    status_code=401,
                    headers={"Cache-Control": "no-store"},
                )
            if (
                request.method not in {"GET", "HEAD", "OPTIONS"}
                and request.headers.get("origin") != self.origin
            ):
                return JSONResponse({"detail": "Same-origin request required"}, status_code=403)
            request.state.login_subject = subject
        response = await call_next(request)
        if not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
            # no-referrer makes native POST forms send Origin: null, which our
            # strict CSRF check correctly rejects. Preserve the origin within
            # the app without disclosing referrers to other sites. OAuth pages
            # retain no-referrer to protect callback codes and login state.
            response.headers["Referrer-Policy"] = (
                "no-referrer" if request.url.path.startswith("/auth/") else "same-origin"
            )
        return response


def install_login(app: FastAPI, values: Mapping[str, str] | None = None) -> None:
    """Install PKCE/state/nonce validation, secure sessions, and the invite-only gate."""
    configuration = login_configuration(os.environ if values is None else values)
    app.state.login_enabled = configuration is not None
    if configuration is None:
        return
    key = load_session_key(configuration)
    oauth = OAuth()
    client = oauth.register(
        "cognito",
        client_id=configuration.client_id,
        server_metadata_url=f"{configuration.issuer}/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": "none",
            "timeout": 15,
        },
    )
    if client is None:
        raise ValueError("Cognito client registration failed")
    app.state.login_client = client

    @app.get("/auth/login", include_in_schema=False)
    async def login(request: Request) -> Response:
        request.session.clear()
        return cast(
            Response,
            await client.authorize_redirect(request, f"{configuration.origin}/auth/callback"),
        )

    @app.get("/auth/callback", include_in_schema=False)
    async def callback(request: Request) -> Response:
        try:
            token = await client.authorize_access_token(
                request,
                claims_options={"iss": {"essential": True, "value": configuration.issuer}},
                leeway=30,
            )
            claims = token.get("userinfo", {})
            subject = claims.get("sub")
            expires = claims.get("exp")
            if (
                not isinstance(subject, str)
                or not subject
                or not isinstance(expires, (int, float))
                or expires <= time.time()
            ):
                raise ValueError("Missing verified identity")
        except Exception:
            request.session.clear()
            return HTMLResponse(
                'Sign-in could not be verified. <a href="/auth/login">Try again</a>.',
                status_code=401,
            )
        # No access, refresh, ID token, provider credential or email enters the cookie.
        request.session.clear()
        request.session["subject"] = subject
        request.session["expires_at"] = min(expires, int(time.time()) + SESSION_SECONDS)
        return RedirectResponse("/workspace", status_code=303)

    @app.post("/auth/logout", include_in_schema=False)
    async def logout(request: Request) -> Response:
        request.session.clear()
        query = urlencode(
            {
                "client_id": configuration.client_id,
                "logout_uri": f"{configuration.origin}/auth/signed-out",
            }
        )
        return RedirectResponse(f"{configuration.domain}/logout?{query}", status_code=303)

    @app.get("/auth/signed-out", include_in_schema=False)
    async def signed_out() -> Response:
        return HTMLResponse(
            (Path(__file__).parent / "templates" / "signed_out.html").read_text(encoding="utf-8")
        )

    app.add_middleware(LoginGate, origin=configuration.origin)
    # Last added middleware is outermost: signed session must exist before LoginGate runs.
    app.add_middleware(
        SessionMiddleware,
        secret_key=key,
        session_cookie=SESSION_COOKIE,
        max_age=SESSION_SECONDS,
        same_site="lax",
        https_only=True,
    )
