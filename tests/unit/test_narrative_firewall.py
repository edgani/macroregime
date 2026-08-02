from eros.thesis.narrative_firewall import Claim, ClaimClass, SourceType, assess_claim


def test_social_post_can_only_open_research_ticket() -> None:
    claim = Claim(
        claim_id="CL-1",
        source_id="SOCIAL-1",
        source_type=SourceType.SOCIAL_MEDIA,
        claim_text="A screenshot says intervention is imminent.",
        claim_class=ClaimClass.FORECAST,
        original_source_chain=["anonymous screenshot"],
        testable_predictions=["Official operation reported within five business days."],
    )
    result = assess_claim(claim)
    assert result.decision_permission == "research_only"
    assert result.material_probability_update_allowed is False


def test_untestable_claim_is_archived() -> None:
    claim = Claim(
        claim_id="CL-2",
        source_id="NEWS-1",
        source_type=SourceType.JOURNALIST_INTERPRETATION,
        claim_text="Officials secretly want a weaker currency forever.",
        claim_class=ClaimClass.ATTRIBUTION,
        original_source_chain=["commentary"],
        testable_predictions=[],
    )
    result = assess_claim(claim)
    assert result.verification_status == "UNTESTABLE_ARCHIVE"
    assert result.decision_permission == "blocked"
