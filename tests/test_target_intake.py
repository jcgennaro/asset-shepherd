"""Acceptance for the minimum-information conversational target contract."""

import pytest

from asset_shepherd.models import AssetTargetUse
from asset_shepherd.target_intake import (
    MINIMUM_TARGET_CONFIDENCE,
    TargetEvidenceSource,
    TargetFieldEvidence,
    TargetIntakeContract,
    clarify_target_intake,
    draft_target_intake,
)


def test_explicit_description_completes_minimum_contract_without_questions() -> None:
    """Use and size stated in prose become a confirmable typed proposal."""
    draft = draft_target_intake(
        "A 1.2 m hanging lantern used as a static environment prop in a dark game level."
    )

    assert draft.ready_for_confirmation
    assert draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert draft.target_height_cm == 120.0
    assert draft.missing_fields == ()
    assert {item.source for item in draft.evidence} == {TargetEvidenceSource.EXPLICIT_USER_TEXT}


def test_only_missing_fields_are_requested_and_clarification_completes_them() -> None:
    """An explicit use is preserved while the absent exact height becomes one question."""
    draft = draft_target_intake("A hanging lantern used as a static environment prop in my game.")

    assert draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert draft.target_height_cm is None
    assert draft.missing_fields == ("target_height_cm",)

    complete = clarify_target_intake(draft, target_height_m="1.2")
    assert complete.ready_for_confirmation
    assert complete.target_height_cm == 120.0
    height_evidence = next(item for item in complete.evidence if item.field == "target_height_cm")
    assert height_evidence.source is TargetEvidenceSource.USER_CLARIFICATION


def test_conflicting_or_absent_use_does_not_silently_choose_a_target() -> None:
    """Ambiguous prose stays incomplete instead of producing a consequential silent guess."""
    draft = draft_target_intake(
        "A 180 cm character that might be a static statue or a playable character."
    )

    assert draft.target_use is None
    assert draft.target_height_cm == 180.0
    assert draft.missing_fields == ("target_use",)

    complete = clarify_target_intake(
        draft,
        target_use_value=AssetTargetUse.PLAYABLE_CHARACTER.value,
    )
    assert complete.ready_for_confirmation
    assert complete.target_use is AssetTargetUse.PLAYABLE_CHARACTER
    use_evidence = next(item for item in complete.evidence if item.field == "target_use")
    assert use_evidence.source is TargetEvidenceSource.USER_CLARIFICATION


def test_contract_rejects_inconsistent_missing_fields_or_uncited_values() -> None:
    """Model output cannot claim readiness without complete internally consistent evidence."""
    with pytest.raises(ValueError, match="missing_fields"):
        TargetIntakeContract(
            description="A complete enough description for strict model validation.",
            target_use=None,
            target_height_cm=None,
            evidence=(),
            missing_fields=(),
        )
    with pytest.raises(ValueError, match="Every populated"):
        TargetIntakeContract(
            description="A complete static asset with a stated 1.2 meter target height.",
            target_use=AssetTargetUse.STATIC_GAME_ASSET,
            target_height_cm=120.0,
            evidence=(),
            missing_fields=(),
        )
    with pytest.raises(ValueError, match="greater than or equal"):
        TargetFieldEvidence(
            field="target_use",
            source=TargetEvidenceSource.EXPLICIT_USER_TEXT,
            confidence=MINIMUM_TARGET_CONFIDENCE - 0.01,
            evidence="An uncertain inference should become a question.",
        )


def test_completed_contract_cannot_be_silently_rewritten_as_clarification() -> None:
    """A new clarification command cannot alter or shadow an already complete proposal."""
    complete = draft_target_intake("A 1.2 m lantern used as a static game asset.")

    with pytest.raises(ValueError, match="already complete"):
        clarify_target_intake(complete, target_height_m="2")
