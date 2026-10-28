import pytest
from freezegun import freeze_time

from app.utils_nl.letters import get_letter_printing_statement, get_letter_validation_error


@pytest.mark.parametrize(
    "created_at, current_datetime",
    [
        ("2017-07-07T09:00:00+00:00", "2017-07-07 09:05:00"),  # just sent
        ("2017-07-07T09:00:00+00:00", "2017-07-07 16:31:00"),  # after 17:30, summer
        ("2017-12-12T18:00:00+00:00", "2017-12-13 17:00:00"),  # sent after 17:30 the day before
        ("2017-12-01T00:00:00+00:00", "2017-12-12 12:00:00"),  # long ago
    ],
)
def test_get_letter_printing_statement_for_many_letters_depends_on_neither_time_nor_status(
    created_at, current_datetime
):
    with freeze_time(current_datetime):
        for status in ("created", "sending", "delivered"):
            assert get_letter_printing_statement(status, created_at) == (
                "NotifyNL stuurt brieven binnen enkele minuten naar de printleverancier."
            )


@pytest.mark.parametrize(
    "created_at, expected_statement",
    [
        ("2017-07-07T09:00:00+00:00", "Verstuurd vandaag"),
        # notifynl-api groups letters uploaded after 17:30 under the next day
        ("2017-07-08T16:30:00+00:00", "Verstuurd vandaag"),
        ("2017-07-06T16:29:00+00:00", "Verstuurd gisteren"),
        ("2017-06-01T00:00:00+00:00", "Verstuurd op 1 juni"),
        ("2017-03-26T12:00:00+00:00", "Verstuurd op 26 maart"),
    ],
)
@freeze_time("2017-07-07 19:00:00")
def test_get_letter_printing_statement_short_form_says_when_the_letters_were_sent(created_at, expected_statement):
    assert get_letter_printing_statement("created", created_at, long_form=False) == expected_statement


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


@pytest.mark.parametrize(
    "validation_message, expected_detail, expected_summary",
    (
        (
            "not-a-real-uk-postcode",
            "De laatste regel van het adres moet een geldige postcode en plaatsnaam zijn.",
            "De validatie is mislukt omdat de laatste regel van het adres geen geldige postcode en plaatsnaam is.",
        ),
        (
            "not-a-real-uk-postcode-or-country",
            "De laatste regel van het adres moet een geldige postcode en plaatsnaam of een ander land zijn.",
            (
                "De validatie is mislukt omdat de laatste regel van het adres geen geldige postcode en plaatsnaam "
                "of een ander land is."
            ),
        ),
    ),
)
def test_get_letter_validation_error_for_invalid_last_address_line_does_not_mention_uk(
    notify_admin, validation_message, expected_detail, expected_summary
):
    # The error codes keep their upstream "uk" names (shared with template-preview and api), but the
    # check behind them is the Dutch postcode + city check, so the message must not ask for a UK postcode.
    with notify_admin.test_request_context():
        error = get_letter_validation_error(validation_message, invalid_pages=[1])

    assert error["detail"] == expected_detail
    assert error["summary"] == expected_summary
    assert "VK" not in error["detail"]
    assert "VK" not in error["summary"]


def test_get_letter_validation_error_for_address_placement_decided_by_the_print_provider(notify_admin):
    with notify_admin.test_request_context():
        error = get_letter_validation_error(
            "address-placement-mismatch",
            letter_address_placement="60mm",
            address_placement_decided_by_provider=True,
        )

    assert error["title"] == "De positie van het adres komt niet overeen met uw printleverancier"
    assert "de printleverancier van uw organisatie gebruikt (60mm)" in error["detail"]
    assert "printleverancier van uw organisatie (60mm)" in error["summary"]
    # the service can't change a placement its print provider decides
    assert "standaard" not in error["detail"] + error["summary"]
    assert "wijzig" not in error["detail"]
