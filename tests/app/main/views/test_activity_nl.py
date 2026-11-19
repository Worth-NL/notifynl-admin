import pytest
from freezegun import freeze_time

from tests.conftest import create_notifications, normalize_spaces


@pytest.mark.parametrize(
    "detailed_status_code, expected_state",
    [
        # marked delivered when the organisation's print provider accepted it, which never reports back
        ("delivered-on-acceptance", "Bezorging niet bevestigd 1 januari om 00:01"),
        # reported delivered by the print provider itself
        (None, "1 januari om 00:01"),
    ],
)
@freeze_time("2026-01-01 00:01")
def test_letter_activity_says_when_delivery_is_not_confirmed(
    client_request,
    service_one,
    mock_get_service_statistics,
    mock_get_service_data_retention,
    mock_get_notifications_count_for_service,
    mock_get_api_keys,
    mocker,
    detailed_status_code,
    expected_state,
):
    notifications = create_notifications(template_type="letter", status="delivered")
    for notification in notifications["notifications"]:
        notification["detailed_status_code"] = detailed_status_code
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications)

    page = client_request.get(
        "main.view_notifications",
        service_id=service_one["id"],
        message_type="letter",
        status="",
    )

    assert normalize_spaces(page.select_one(".notification-state").text) == expected_state
