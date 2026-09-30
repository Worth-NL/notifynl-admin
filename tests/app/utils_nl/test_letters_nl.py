import pytest
from freezegun import freeze_time

from app.utils_nl.letters import get_letter_printing_statement, get_letter_validation_error


@pytest.mark.parametrize(
    "created_at, current_datetime",
    [
        ("2017-07-07T12:00:00+00:00", "2017-07-07 16:29:00"),  # created today, summer
        ("2017-12-12T12:00:00+00:00", "2017-12-12 17:29:00"),  # created today, winter
    ],
)
def test_get_letter_printing_statement_for_a_letter_still_to_be_sent(created_at, current_datetime):
    with freeze_time(current_datetime):
        assert get_letter_printing_statement("created", created_at) == "Wordt naar de printleverancier gestuurd"
        assert get_letter_printing_statement("created", created_at, long_form=False) == (
            "Wordt naar de printleverancier gestuurd"
        )


@pytest.mark.parametrize(
    "created_at, expected_day",
    [
        ("2017-07-07T09:00:00+00:00", "vandaag"),
        ("2017-07-06T16:29:00+00:00", "gisteren"),
        ("2017-12-01T00:00:00+00:00", "op 1 december"),
        ("2017-03-26T12:00:00+00:00", "op 26 maart"),
    ],
)
@freeze_time("2017-07-07 12:00:00")
def test_get_letter_printing_statement_for_a_letter_that_has_been_sent(created_at, expected_day):
    assert get_letter_printing_statement("delivered", created_at) == f"Naar de printleverancier gestuurd {expected_day}"
    assert get_letter_printing_statement("delivered", created_at, long_form=False) == f"Verstuurd {expected_day}"


@pytest.mark.parametrize("status", ["created", "sending", "sent", "delivered"])
@freeze_time("2017-07-07 12:00:00")
def test_get_letter_printing_statement_never_mentions_a_print_run(status):
    # letters go to their print provider within minutes, there's no daily print run
    for created_at in ("2017-07-07T11:00:00+00:00", "2017-07-01T11:00:00+00:00"):
        assert "17:30" not in get_letter_printing_statement(status, created_at)
        assert "print" not in get_letter_printing_statement(status, created_at).lower().replace("printleverancier", "")


@pytest.mark.parametrize(
    "letter_address_placement, expected_label",
    (
        ("50mm", "50mm"),
        ("60mm", "60mm (standaard)"),
    ),
)
def test_get_letter_validation_error_for_address_placement_mismatch_interpolates_configured_placement(
    notify_admin, letter_address_placement, expected_label
):
    with notify_admin.test_request_context():
        error = get_letter_validation_error(
            "address-placement-mismatch",
            letter_address_placement=letter_address_placement,
        )

    assert expected_label in error["detail"]
    assert expected_label in error["summary"]
    # The Pingen/"standaard" settings-page branding must not leak into this message - see
    # AdminServiceLetterAddressPlacementForm.choices for where "Pingen" is intentionally kept.
    assert "Pingen" not in error["detail"]
    assert "Pingen" not in error["summary"]
