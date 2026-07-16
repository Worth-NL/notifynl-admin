import pytest

from app.overrides_nl.formatters import format_notification_type


@pytest.mark.parametrize(
    ("notification_type", "expected"),
    [
        ("email", "E-mail"),
        ("sms", "SMS"),
        ("letter", "Brief"),
        ("messagebox", "Berichtenbox"),
    ],
)
def test_format_notification_type(notification_type, expected):
    assert format_notification_type(notification_type) == expected
