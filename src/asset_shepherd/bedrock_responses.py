"""Shared Amazon Bedrock Responses endpoint and short-term-token helpers."""

from __future__ import annotations

import re
from collections.abc import Callable

from aws_bedrock_token_generator import provide_token  # pyright: ignore[reportMissingTypeStubs]

BedrockTokenProvider = Callable[[str], str]

_REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+$")
_INFERENCE_PROFILE_PATTERN = re.compile(r"^(?:us|global|in|us-gov)\.openai\.[a-z0-9][a-z0-9.-]*$")


def validate_bedrock_region(region: str) -> str:
    """Validate one AWS region before interpolating it into a service URL."""
    if not _REGION_PATTERN.fullmatch(region):
        raise ValueError("Invalid Amazon Bedrock region")
    return region


def validate_bedrock_responses_model_id(model_id: str) -> str:
    """Require the geographic/global inference profile expected by bedrock-runtime."""
    if not _INFERENCE_PROFILE_PATTERN.fullmatch(model_id):
        raise ValueError(
            "Amazon Bedrock Responses requires an OpenAI geographic or global inference profile"
        )
    return model_id


def bedrock_responses_base_url(region: str) -> str:
    """Return the recommended OpenAI-compatible bedrock-runtime base URL."""
    validated = validate_bedrock_region(region)
    return f"https://bedrock-runtime.{validated}.amazonaws.com/openai/v1"


def provide_bedrock_token(region: str) -> str:
    """Mint or reuse a short-term IAM-derived Bedrock bearer token."""
    return provide_token(region=validate_bedrock_region(region))
