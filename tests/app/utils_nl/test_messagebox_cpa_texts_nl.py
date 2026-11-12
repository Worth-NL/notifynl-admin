import pytest

from app.utils_nl.messagebox_cpa_texts import dutch_assessment, dutch_cpa_text, dutch_listing

PREPROD = "preprod-globe-ebms-internet.procesinfrastructuur.nl"


@pytest.mark.parametrize(
    "english, dutch",
    [
        ("ebms-core accepts the CPA", "ebms-core accepteert de CPA"),
        ("ebms-core rejects the CPA: 500 Invalid version", "ebms-core weigert de CPA: 500 Invalid version"),
        ("The CPA has 3 parties instead of 2", "De CPA heeft 3 partijen in plaats van 2"),
        (
            "Our party also lists other endpoints than https://ebms.example.invalid/ebms",
            "Onze partij heeft ook andere endpoints dan https://ebms.example.invalid/ebms",
        ),
        ("http://x.invalid/ebms doesn't use https", "http://x.invalid/ebms gebruikt geen https"),
        (
            f"globe-ebms-internet.procesinfrastructuur.nl isn't allowed for live (allowed: {PREPROD})",
            f"globe-ebms-internet.procesinfrastructuur.nl is niet toegestaan voor live (toegestaan: {PREPROD})",
        ),
        (
            "x.invalid isn't allowed for team (allowed: none)",
            "x.invalid is niet toegestaan voor team (toegestaan: geen)",
        ),
        (f"{PREPROD} is allowed for team", f"{PREPROD} is toegestaan voor team"),
        (
            "Our party sends GLOBE-R-BV-Request as Afnemer to Leverancier (MijnOverheid_BB_R)",
            "Onze partij verstuurt GLOBE-R-BV-Request als Afnemer naar Leverancier (MijnOverheid_BB_R)",
        ),
        ("The CPA's status is not set", "De CPA heeft geen status"),
        ("The CPA's status is agreed", "De status van de CPA is agreed"),
        ("Valid from 2026-11-05 to 2028-03-31", "Geldig van 2026-11-05 tot 2028-03-31"),
        (
            "Valid from 2026-11-24 to 2028-03-31; it can be selected from 2026-11-24",
            "Geldig van 2026-11-24 tot 2028-03-31; te kiezen vanaf 2026-11-24",
        ),
        ("Ended: valid from 2024-01-01 to 2025-01-01", "Verlopen: geldig van 2024-01-01 tot 2025-01-01"),
        ("The CPA ends on 2026-12-31", "De CPA loopt af op 2026-12-31"),
        (
            "Certificate cert-1 of Logius expires on 2026-12-01",
            "Certificaat cert-1 van Logius verloopt op 2026-12-01",
        ),
        ("The CPA can't be used for live", "De CPA kan niet worden gebruikt voor live"),
        ("ebms-core already has a CPA with id EXAMPLE-CPA", "ebms-core heeft al een CPA met id EXAMPLE-CPA"),
        ("ebms-core can't return the CPA: 404", "ebms-core kan de CPA niet teruggeven: 404"),
    ],
)
def test_dutch_cpa_text(english, dutch):
    assert dutch_cpa_text(english) == dutch


@pytest.mark.parametrize("text", ["CPA is not well-formed: line 1", "", None])
def test_dutch_cpa_text_keeps_what_it_does_not_know(text):
    assert dutch_cpa_text(text) == text


def test_dutch_assessment_and_listing_leave_the_rest_alone():
    assessment = {
        "purpose": "team",
        "eligible": True,
        "checks": [{"name": "parties", "passed": True, "message": "The CPA has 2 parties"}],
        "warnings": ["The CPA ends on 2026-12-31"],
    }
    listing = {"cpa_id": "X", "summary": None, "error": None, "assessments": {"team": assessment}, "selected_for": []}

    assert dutch_listing(listing) == {
        **listing,
        "assessments": {
            "team": {
                **assessment,
                "checks": [{"name": "parties", "passed": True, "message": "De CPA heeft 2 partijen"}],
                "warnings": ["De CPA loopt af op 2026-12-31"],
            }
        },
    }
    assert assessment["warnings"] == ["The CPA ends on 2026-12-31"]
    assert dutch_assessment(None) is None
