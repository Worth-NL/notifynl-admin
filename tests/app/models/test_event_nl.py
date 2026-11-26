import pytest

from app.models_nl.event import ServiceEvent
from tests.conftest import sample_uuid


@pytest.mark.parametrize(
    "value_from, value_to, expected",
    (
        (50, 999_999_999, "Increased de dagelijkse berichtenboxlimiet van deze service van 50 naar 999,999,999"),
        (999_999_999, 50, "Reduced de dagelijkse berichtenboxlimiet van deze service van 999,999,999 naar 50"),
    ),
)
def test_service_event_messagebox_message_limit(value_from, value_to, expected):
    event = ServiceEvent(
        {"created_at": "foo", "updated_at": "bar", "created_by_id": sample_uuid()},
        "messagebox_message_limit",
        value_from,
        value_to,
    )
    assert event.relevant is True
    assert str(event) == expected
