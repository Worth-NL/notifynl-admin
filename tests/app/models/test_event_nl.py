import pytest

from app.models_nl.event import ServiceEvent
from tests.conftest import sample_uuid


@pytest.mark.parametrize(
    "key, value_from, value_to, expected",
    (
        ("active", True, False, "Verwijderde deze service"),
        ("active", False, True, "Hief de opschorting van deze service op"),
        ("message_limit", 50, 250_000, "Verhoogde de dagelijkse berichtlimiet van deze service van 50 naar 250,000"),
        ("message_limit", 250_000, 50, "Verlaagde de dagelijkse berichtlimiet van deze service van 250,000 naar 50"),
        (
            "email_message_limit",
            50,
            250_000,
            "Verhoogde de dagelijkse e-maillimiet van deze service van 50 naar 250,000",
        ),
        (
            "email_message_limit",
            250_000,
            50,
            "Verlaagde de dagelijkse e-maillimiet van deze service van 250,000 naar 50",
        ),
        ("sms_message_limit", 50, 250_000, "Verhoogde de dagelijkse sms-limiet van deze service van 50 naar 250,000"),
        ("sms_message_limit", 250_000, 50, "Verlaagde de dagelijkse sms-limiet van deze service van 250,000 naar 50"),
        (
            "letter_message_limit",
            50,
            250_000,
            "Verhoogde de dagelijkse letterlimiet van deze service van 50 naar 250,000",
        ),
        (
            "letter_message_limit",
            250_000,
            50,
            "Verlaagde de dagelijkse letterlimiet van deze service van 250,000 naar 50",
        ),
        (
            "messagebox_message_limit",
            50,
            999_999_999,
            "Verhoogde de dagelijkse berichtenboxlimiet van deze service van 50 naar 999,999,999",
        ),
        (
            "messagebox_message_limit",
            999_999_999,
            50,
            "Verlaagde de dagelijkse berichtenboxlimiet van deze service van 999,999,999 naar 50",
        ),
    ),
)
def test_service_event(key, value_from, value_to, expected):
    event = ServiceEvent(
        {"created_at": "foo", "updated_at": "bar", "created_by_id": sample_uuid()},
        key,
        value_from,
        value_to,
    )
    assert event.relevant is True
    assert str(event) == expected
