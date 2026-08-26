import pytest
from freezegun import freeze_time

from app.utils_nl.letters import get_letter_printing_statement, get_letter_validation_error, printing_today_or_tomorrow


@pytest.mark.parametrize(
    "utc_datetime",
    [
        "2018-08-01T23:00:00+00:00",
        "2018-08-01T16:29:00+00:00",
        "2018-11-01T00:00:00+00:00",
        "2018-11-01T10:00:00+00:00",
        "2018-11-01T17:29:00+00:00",
    ],
)
def test_printing_today_or_tomorrow_returns_vandaag(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == "vandaag"


@pytest.mark.parametrize(
    "utc_datetime",
    [
        "2018-08-01T22:59:00+00:00",
        "2018-08-01T16:30:00+00:00",
        "2018-11-01T17:30:00+00:00",
        "2018-11-01T21:00:00+00:00",
        "2018-11-01T23:59:00+00:00",
    ],
)
def test_printing_today_or_tomorrow_returns_morgen(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == "morgen"


@pytest.mark.parametrize(
    "created_at, current_datetime",
    [
        ("2017-07-07T12:00:00+00:00", "2017-07-07 16:29:00"),  # created today, summer
        ("2017-07-06T23:30:00+00:00", "2017-07-07 16:29:00"),  # created just after midnight, summer
        ("2017-12-12T12:00:00+00:00", "2017-12-12 17:29:00"),  # created today, winter
        ("2017-12-12T21:30:00+00:00", "2017-12-13 17:29:00"),  # created after 5:30pm yesterday
        ("2017-03-25T17:31:00+00:00", "2017-03-26 16:29:00"),  # over clock change period on 2017-03-26
    ],
)
def test_get_letter_printing_statement_when_letter_prints_vandaag(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement("created", created_at)

    assert statement == "Het printen start vandaag om 17:30 uur"


@pytest.mark.parametrize(
    "created_at, current_datetime",
    [
        ("2017-07-07T16:31:00+00:00", "2017-07-07 22:59:00"),  # created today, summer
        ("2017-12-12T17:31:00+00:00", "2017-12-12 23:59:00"),  # created today, winter
    ],
)
def test_get_letter_printing_statement_when_letter_prints_morgen(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement("created", created_at)

    assert statement == "Het printen start morgen om 17:30 uur"


def test_get_letter_printing_statement_short_form():
    with freeze_time("2017-07-07 16:29:00"):
        statement = get_letter_printing_statement("created", "2017-07-07T12:00:00+00:00", long_form=False)

    assert statement == "Printen vandaag om 17:30 uur"


@pytest.mark.parametrize(
    "created_at, expected_print_day",
    [
        ("2017-07-06T16:29:00+00:00", "gisteren"),
        ("2017-12-01T00:00:00+00:00", "op 1 december"),
        ("2017-03-26T12:00:00+00:00", "op 26 maart"),
    ],
)
@freeze_time("2017-07-07 12:00:00")
def test_get_letter_printing_statement_for_letter_that_has_been_sent(created_at, expected_print_day):
    statement = get_letter_printing_statement("delivered", created_at)

    assert statement == f"Geprint {expected_print_day} om 17:30 uur"


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
