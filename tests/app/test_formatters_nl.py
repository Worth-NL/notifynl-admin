from types import SimpleNamespace

import pytest

from app.overrides_nl.formatters import format_notification_status_text, format_notification_type


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


def _notification(*, template_type="messagebox", **kwargs):
    # `notification.template` is a plain dict on a real Notification model
    # (see e.g. its `content`/`redact_personalisation` properties), not a
    # nested object -- Jinja's `.` operator falls back to dict access
    # transparently, but plain Python code (like this filter) must not.
    return SimpleNamespace(template={"template_type": template_type}, **kwargs)


def test_format_notification_status_text_shows_reason_and_code_for_messagebox_failure():
    notification = _notification(
        notification_type="messagebox",
        status="permanent-failure",
        messagebox_failure_reason="OIN uit CPA komt niet overeen met OID in het bericht",
        detailed_status_code="OinInCPAKomtNietOvereenMetOinInBericht",
    )
    assert format_notification_status_text(notification) == (
        "OIN uit CPA komt niet overeen met OID in het bericht (OinInCPAKomtNietOvereenMetOinInBericht)"
    )


def test_format_notification_status_text_falls_back_without_reason():
    notification = _notification(
        notification_type="messagebox",
        status="sending",
        messagebox_failure_reason=None,
        detailed_status_code=None,
    )
    assert format_notification_status_text(notification) == "Aan het afleveren"


def test_format_notification_status_text_falls_back_when_reason_attr_missing():
    # Simulates a notification whose annotated attribute was never set because
    # the key wasn't present in the underlying API response dict at all --
    # JSONModel's __init__ is lenient, so accessing it must not raise.
    notification = SimpleNamespace(
        notification_type="messagebox",
        status="technical-failure",
        template={"template_type": "messagebox"},
    )
    assert format_notification_status_text(notification) == "Technische fout"


def test_format_notification_status_text_ignores_reason_for_non_messagebox():
    notification = _notification(
        template_type="sms",
        notification_type="sms",
        status="permanent-failure",
        messagebox_failure_reason="should be ignored",
        detailed_status_code="should-be-ignored",
    )
    assert format_notification_status_text(notification) == "Niet afgeleverd"
