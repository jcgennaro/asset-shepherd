"""Deployment-owned provider selection and server-only OpenAI secret retrieval."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, cast

import boto3

from asset_shepherd.bedrock_converse import (
    resolve_bedrock_converse_model,
    supported_bedrock_converse_models,
)

OPENAI_LUNA_ID = "gpt-5.6-luna"
OPENAI_SECRET_SETTING = "ASSET_SHEPHERD_OPENAI_SECRET_ARN"


class _SecretClient(Protocol):
    def get_secret_value(self, *, SecretId: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class HostedModel:
    """Public model metadata, never a credential or browser-selected endpoint."""

    model_id: str
    display_name: str
    hint: str
    provider: Literal["bedrock-converse", "openai"]
    recommended: bool = False


def resolve_hosted_model(model_id: str) -> HostedModel:
    """Resolve only explicitly supported model/provider pairs."""
    if model_id == OPENAI_LUNA_ID:
        return HostedModel(
            model_id,
            "Luna xhigh — OpenAI API",
            "Cost-conscious visual reasoning. Uses OpenAI, billed separately from AWS credits.",
            "openai",
        )
    model = resolve_bedrock_converse_model(model_id)
    return HostedModel(
        model.model_id, model.display_name, model.hint, "bedrock-converse", model.recommended
    )


def _allowed_models(values: Mapping[str, str]) -> set[str]:
    return {
        item.strip()
        for item in values.get("ASSET_SHEPHERD_ALLOWED_MODEL_IDS", "").split(",")
        if item.strip()
    }


def hosted_model_choices(values: Mapping[str, str]) -> tuple[HostedModel, ...]:
    """Keep local single-provider behavior; require explicit opt-in for hosted OpenAI."""
    allowed = _allowed_models(values)
    if values.get("ASSET_SHEPHERD_MODEL_PROVIDER") != "bedrock-converse" and not values.get(
        OPENAI_SECRET_SETTING
    ):
        return ()
    choices = [
        resolve_hosted_model(model.model_id)
        for model in supported_bedrock_converse_models()
        if not allowed or model.model_id in allowed
    ]
    if OPENAI_LUNA_ID in allowed and values.get(OPENAI_SECRET_SETTING):
        choices.append(resolve_hosted_model(OPENAI_LUNA_ID))
    return tuple(choices)


def load_openai_secret(arn: str, region: str, aws_profile: str | None = None) -> str:
    """Fetch the exact configured secret into memory; suppress credential-bearing errors."""
    if not re.fullmatch(
        r"arn:aws:secretsmanager:"
        + re.escape(region)
        + r":\d{12}:secret:asset-shepherd/[a-z0-9-]+/openai-[A-Za-z0-9]{6}",
        arn,
    ):
        raise ValueError("Invalid deployment-owned OpenAI secret reference")
    try:
        session = boto3.Session(profile_name=aws_profile, region_name=region)
        client = cast(
            _SecretClient,
            session.client("secretsmanager"),  # pyright: ignore[reportUnknownMemberType]
        )
        response = client.get_secret_value(SecretId=arn)
        payload = json.loads(cast(str, response["SecretString"]))
        key = payload.get("api_key")
        if not isinstance(key, str) or not key.startswith("sk-") or len(key) < 20:
            raise ValueError("Invalid key")
    except Exception:
        raise ValueError("The configured OpenAI credential could not be loaded") from None
    return key


def hosted_model_values(model_id: str, settings: Mapping[str, str]) -> dict[str, str]:
    """Rebuild the persisted choice from trusted configuration, without silent fallback."""
    model = resolve_hosted_model(model_id)
    allowed = _allowed_models(settings)
    if allowed and model.model_id not in allowed:
        raise ValueError("The workspace model is not enabled in this deployment")
    values = dict(settings)
    values.pop("OPENAI_API_KEY", None)
    values.pop("ASSET_SHEPHERD_OPENAI_RESPONSES_URL", None)
    values["ASSET_SHEPHERD_MODEL_ID"] = model.model_id
    values["ASSET_SHEPHERD_INTAKE_MODEL"] = model.model_id
    values["ASSET_SHEPHERD_MODEL_PROVIDER"] = model.provider
    values["ASSET_SHEPHERD_INTAKE_PROVIDER"] = model.provider
    values.pop("ASSET_SHEPHERD_WORKFLOW_REASONING", None)
    values.pop("ASSET_SHEPHERD_INTAKE_REASONING", None)
    if model.provider == "openai":
        arn = settings.get(OPENAI_SECRET_SETTING, "")
        region = settings.get("ASSET_SHEPHERD_AWS_REGION", settings.get("AWS_REGION", ""))
        if model.model_id not in allowed or not arn or not region:
            raise ValueError("OpenAI is not enabled in this deployment")
        values["OPENAI_API_KEY"] = load_openai_secret(arn, region, settings.get("AWS_PROFILE"))
        values["ASSET_SHEPHERD_WORKFLOW_REASONING"] = "xhigh"
        values["ASSET_SHEPHERD_INTAKE_REASONING"] = "xhigh"
    if values.get("ASSET_SHEPHERD_WORKSPACE_BUCKET"):
        values.setdefault(
            "ASSET_SHEPHERD_SESSION_BUCKET", values["ASSET_SHEPHERD_WORKSPACE_BUCKET"]
        )
    return values
