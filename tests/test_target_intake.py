"""Acceptance for the minimum-information conversational target contract."""

import pytest

from asset_shepherd.models import AssetEndpoint, AssetTargetUse, AssetViewingUse
from asset_shepherd.target_intake import (
    MINIMUM_TARGET_CONFIDENCE,
    TargetEvidenceSource,
    TargetFieldEvidence,
    TargetIntakeContract,
    clarify_target_intake,
    draft_target_intake,
    revise_target_intake,
)


def test_explicit_description_completes_minimum_contract_without_questions() -> None:
    """Use and size stated in prose become a confirmable typed proposal."""
    draft = draft_target_intake(
        "A 1.2 m hanging lantern used as a static environment prop in a dark game level."
    )

    assert draft.ready_for_confirmation
    assert draft.asset_name == "Hanging Lantern"
    assert draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert draft.target_height_cm == 120.0
    assert draft.missing_fields == ()
    assert {item.source for item in draft.evidence} == {
        TargetEvidenceSource.EXPLICIT_USER_TEXT,
        TargetEvidenceSource.DETERMINISTIC_FALLBACK,
    }
    assert draft.target_dimensions_cm == (120.0, 120.0, 120.0)


def test_only_missing_fields_are_requested_and_clarification_completes_them() -> None:
    """An explicit use is preserved while the absent exact height becomes one question."""
    draft = draft_target_intake("A hanging lantern used as a static environment prop in my game.")

    assert draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert draft.target_height_cm is None
    assert draft.missing_fields == ("target_dimensions_cm",)

    complete = clarify_target_intake(draft, target_height_m="1.2")
    assert complete.ready_for_confirmation
    assert complete.target_height_cm == 120.0
    bounds_evidence = next(
        item for item in complete.evidence if item.field == "target_dimensions_cm"
    )
    assert bounds_evidence.source is TargetEvidenceSource.USER_CLARIFICATION


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


def test_user_can_explicitly_replace_an_unconfirmed_model_proposal() -> None:
    """Adjustment replaces both proposal fields with user evidence and preserves origin."""
    draft = draft_target_intake("A 1.2 m lantern used as a static game asset.")
    revised = revise_target_intake(
        draft,
        target_use_value=AssetTargetUse.RIG_READY_CHARACTER.value,
        target_height_m="1.75",
    )

    assert revised.target_use is AssetTargetUse.RIG_READY_CHARACTER
    assert revised.target_height_cm == 175.0
    assert revised.description == draft.description
    assert revised.analyzer_provider == draft.analyzer_provider
    assert {item.source for item in revised.evidence} == {TargetEvidenceSource.USER_CLARIFICATION}


def test_canonical_endpoint_clarification_discards_stale_other_detail() -> None:
    """Browser-restored Other text cannot invalidate a canonical engine choice."""
    draft = TargetIntakeContract(
        schema_version=6,
        description="A static dog helmet measuring about 18 by 16 by 20 centimeters.",
        asset_name="Dog Helmet",
        analyzer_provider="gemini",
        analyzer_model="gemini-3.8-flash",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=16.0,
        endpoint=None,
        endpoint_detail=None,
        viewing_use=AssetViewingUse.NORMAL_GAMEPLAY,
        target_dimensions_cm=(18.0, 16.0, 20.0),
        evidence=(
            TargetFieldEvidence(
                field="target_use",
                source=TargetEvidenceSource.MODEL_INFERENCE,
                confidence=0.99,
                evidence="The description identifies a static game prop.",
            ),
            TargetFieldEvidence(
                field="target_dimensions_cm",
                source=TargetEvidenceSource.MODEL_INFERENCE,
                confidence=0.99,
                evidence="The description supplies all three target dimensions.",
            ),
            TargetFieldEvidence(
                field="viewing_use",
                source=TargetEvidenceSource.DETERMINISTIC_FALLBACK,
                confidence=1.0,
                evidence="Normal gameplay is the default viewing use.",
            ),
        ),
        missing_fields=("endpoint",),
    )

    complete = clarify_target_intake(
        draft,
        endpoint_value=AssetEndpoint.UNREAL.value,
        endpoint_detail="stale browser value",
        viewing_use_value=AssetViewingUse.NORMAL_GAMEPLAY.value,
    )

    assert complete.endpoint is AssetEndpoint.UNREAL
    assert complete.endpoint_detail is None


def test_canonical_endpoint_revision_discards_stale_other_detail() -> None:
    """The explicit target-revision boundary applies the same endpoint invariant."""
    draft = draft_target_intake("A 1.2 m lantern used as a static game asset.")

    revised = revise_target_intake(
        draft,
        target_use_value=AssetTargetUse.STATIC_GAME_ASSET.value,
        endpoint_value=AssetEndpoint.UNITY.value,
        endpoint_detail="restored custom engine",
        viewing_use_value=AssetViewingUse.CLOSE_UP_SHOWCASE.value,
        target_height_m="1.2",
    )

    assert revised.endpoint is AssetEndpoint.UNITY
    assert revised.endpoint_detail is None
