"""Optional adapter for the official Khronos glTF Validator executable."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal, cast

from pydantic import JsonValue

from asset_shepherd.models import ContractModel, NonNegativeInt

KHRONOS_VALIDATOR_ENV = "ASSET_SHEPHERD_GLTF_VALIDATOR"


class KhronosValidationResult(ContractModel):
    """Stable summary plus the complete official validator report."""

    schema_version: Literal[1] = 1
    validator_version: str
    error_count: NonNegativeInt
    warning_count: NonNegativeInt
    info_count: NonNegativeInt
    hint_count: NonNegativeInt
    issue_codes: tuple[str, ...]
    error_codes: tuple[str, ...]
    error_fingerprints: tuple[str, ...]
    warning_codes: tuple[str, ...]
    report: dict[str, JsonValue]

    @property
    def passed(self) -> bool:
        """Return whether the official validator reported no errors."""
        return self.error_count == 0


class KhronosValidatorUnavailable(RuntimeError):
    """Raised when no configured official validator executable is available."""


class KhronosValidatorError(RuntimeError):
    """Raised when the official validator cannot produce a readable report."""


def find_khronos_validator(configured: Path | None = None) -> Path | None:
    """Resolve an explicitly configured or PATH-installed validator executable."""
    if configured is not None:
        candidate = configured.expanduser().resolve(strict=False)
        return candidate if candidate.is_file() else None
    configured_value = os.environ.get(KHRONOS_VALIDATOR_ENV)
    if configured_value:
        candidate = Path(configured_value).expanduser().resolve(strict=False)
        return candidate if candidate.is_file() else None
    discovered = shutil.which("gltf_validator") or shutil.which("gltf_validator.exe")
    return Path(discovered).resolve() if discovered else None


def _required_count(issues: dict[str, object], key: str) -> int:
    value = issues.get(key)
    if not isinstance(value, int) or value < 0:
        raise KhronosValidatorError(f"Official validator report has invalid {key}")
    return value


def parse_khronos_report(raw: object) -> KhronosValidationResult:
    """Validate and summarize one JSON value emitted by the official validator."""
    if not isinstance(raw, dict):
        raise KhronosValidatorError("Official validator report must be a JSON object")
    report = cast(dict[str, object], raw)
    issues_value = report.get("issues")
    if not isinstance(issues_value, dict):
        raise KhronosValidatorError("Official validator report has no issues object")
    issues = cast(dict[str, object], issues_value)
    messages_value = issues.get("messages", [])
    if not isinstance(messages_value, list):
        raise KhronosValidatorError("Official validator issue messages must be a list")
    issue_codes: list[str] = []
    error_codes: list[str] = []
    error_fingerprints: list[str] = []
    warning_codes: list[str] = []
    for message_value in cast(list[object], messages_value):
        if not isinstance(message_value, dict):
            continue
        message = cast(dict[str, object], message_value)
        code = message.get("code")
        if not isinstance(code, str):
            continue
        issue_codes.append(code)
        if message.get("severity") == 0:
            error_codes.append(code)
            pointer = message.get("pointer")
            detail = message.get("message")
            error_fingerprints.append(
                "|".join(
                    (
                        code,
                        pointer if isinstance(pointer, str) else "",
                        detail if isinstance(detail, str) else "",
                    )
                )
            )
        elif message.get("severity") == 1:
            warning_codes.append(code)
    version = report.get("validatorVersion")
    if not isinstance(version, str) or not version:
        raise KhronosValidatorError("Official validator report has no validator version")
    return KhronosValidationResult(
        validator_version=version,
        error_count=_required_count(issues, "numErrors"),
        warning_count=_required_count(issues, "numWarnings"),
        info_count=_required_count(issues, "numInfos"),
        hint_count=_required_count(issues, "numHints"),
        issue_codes=tuple(issue_codes),
        error_codes=tuple(error_codes),
        error_fingerprints=tuple(error_fingerprints),
        warning_codes=tuple(warning_codes),
        report=cast(dict[str, JsonValue], report),
    )


def validate_with_khronos(
    asset: Path,
    *,
    executable: Path | None = None,
    timeout_seconds: float = 60.0,
) -> KhronosValidationResult:
    """Run the official validator without a shell and return its structured report."""
    validator = find_khronos_validator(executable)
    if validator is None:
        raise KhronosValidatorUnavailable(
            f"Set {KHRONOS_VALIDATOR_ENV} to the official gltf_validator executable"
        )
    source = asset.resolve(strict=True)
    try:
        completed = subprocess.run(
            [str(validator), "-o", str(source)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise KhronosValidatorError(f"Official validator execution failed: {error}") from error
    try:
        raw: object = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = completed.stderr.strip() or "no diagnostic output"
        raise KhronosValidatorError(
            f"Official validator returned no JSON report: {detail}"
        ) from error
    return parse_khronos_report(raw)
