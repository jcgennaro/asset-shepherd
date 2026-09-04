"""Validated optional Amazon Bedrock Guardrail configuration."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

_GUARDRAIL_ID_PATTERN = re.compile(r"[a-z0-9]{1,64}")
_GUARDRAIL_VERSION_PATTERN = re.compile(r"[1-9][0-9]{0,7}")


@dataclass(frozen=True)
class BedrockGuardrailConfiguration:
    """One immutable Guardrail version used by deployed Bedrock inference."""

    identifier: str
    version: str


def load_optional_bedrock_guardrail(
    values: Mapping[str, str],
) -> BedrockGuardrailConfiguration | None:
    """Load a complete immutable Guardrail pair or reject ambiguous configuration."""
    identifier = values.get("ASSET_SHEPHERD_BEDROCK_GUARDRAIL_ID")
    version = values.get("ASSET_SHEPHERD_BEDROCK_GUARDRAIL_VERSION")
    if identifier is None and version is None:
        return None
    if not identifier or not version:
        raise ValueError("Amazon Bedrock Guardrail ID and version must be configured together")
    if _GUARDRAIL_ID_PATTERN.fullmatch(identifier) is None:
        raise ValueError("Amazon Bedrock Guardrail ID is invalid")
    if _GUARDRAIL_VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError("Amazon Bedrock Guardrail version must be an immutable numeric version")
    return BedrockGuardrailConfiguration(identifier=identifier, version=version)
