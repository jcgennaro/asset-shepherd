"""Render a traceable real-world validation report from typed evidence records."""

import argparse
from collections import Counter
from pathlib import Path

from asset_shepherd.validation.models import Adjudication, AssetProvenance


def render_validation_report(
    provenance: AssetProvenance,
    adjudication: Adjudication,
) -> str:
    """Render an honest case-study report without inventing missing evidence."""
    if provenance.asset_id != adjudication.asset_id:
        raise ValueError("Provenance and adjudication asset IDs do not match")
    classifications = Counter(finding.classification for finding in adjudication.findings)
    classification_lines = [
        f"- {classification.value}: {count}" for classification, count in classifications.items()
    ] or ["- No findings adjudicated."]
    raw_minutes = adjudication.manual_minutes_raw_to_usable
    shepherd_minutes = adjudication.manual_minutes_after_shepherd
    saved_minutes = (
        raw_minutes - shepherd_minutes
        if raw_minutes is not None and shepherd_minutes is not None
        else None
    )
    saved_minutes_text = saved_minutes if saved_minutes is not None else "NOT_COMPUTABLE"
    return (
        f"# Real-world validation report: {provenance.display_name}\n\n"
        "## Provenance\n\n"
        f"- Asset ID: `{provenance.asset_id}`\n"
        f"- Generator: {provenance.generator}\n"
        f"- Model or mode: {provenance.model_or_mode or 'NOT_RECORDED'}\n"
        f"- Raw SHA-256: `{provenance.raw_sha256 or 'NOT_REGISTERED'}`\n"
        f"- Public-use confirmed: {str(provenance.public_use_confirmed).lower()}\n"
        f"- Product version: `{adjudication.product_version or 'NOT_RECORDED'}`\n\n"
        "## Finding adjudication\n\n"
        f"{'\n'.join(classification_lines)}\n\n"
        f"- Missed required repairs: {len(adjudication.missed_required_repairs)}\n"
        f"- False severe findings: {len(adjudication.false_severe_findings)}\n"
        f"- Unsafe automatic repairs: {len(adjudication.unsafe_automatic_repairs)}\n"
        f"- Correctly blocked cases: {len(adjudication.correctly_blocked_cases)}\n\n"
        "## Downstream evidence\n\n"
        f"- Raw Unreal result: {adjudication.raw_unreal_result or 'NOT_RECORDED'}\n"
        f"- Shepherd Unreal result: {adjudication.shepherd_unreal_result or 'NOT_RECORDED'}\n"
        "- Human-reference Unreal result: "
        f"{adjudication.human_reference_unreal_result or 'NOT_RECORDED'}\n"
        "- Visual fidelity: "
        f"{adjudication.visual_fidelity_assessment or 'REQUIRES_HUMAN_ADJUDICATION'}\n\n"
        "## Manual effort\n\n"
        f"- Raw to usable: {raw_minutes if raw_minutes is not None else 'NOT_RECORDED'} minutes\n"
        "- After Asset Shepherd: "
        f"{shepherd_minutes if shepherd_minutes is not None else 'NOT_RECORDED'} minutes\n"
        f"- Observed minutes saved: {saved_minutes_text}\n\n"
        "## Claim boundary\n\n"
        "This is case-study evidence for one registered asset. It is not an industry-wide accuracy "
        "claim. Every public claim must link to the underlying frozen artifacts.\n"
    )


def main() -> None:
    """Render one report from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    provenance = AssetProvenance.model_validate_json(args.provenance.read_text(encoding="utf-8"))
    adjudication = Adjudication.model_validate_json(args.adjudication.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_validation_report(provenance, adjudication),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
