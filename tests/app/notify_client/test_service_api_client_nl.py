import pytest

from app.notify_client.service_api_client import ServiceAPIClient
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize(
    "status, kwargs",
    (
        ("on", {}),
        ("off", {"permissions": ["email"]}),
    ),
)
def test_client_update_status_sets_all_daily_limits(notify_admin, mocker, status, kwargs):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_post = mocker.patch.object(client, "post", return_value={"data": {"id": None}})
    mocker.patch("app.notify_client.current_user", id="123")

    client.update_status(SERVICE_ONE_ID, status, **kwargs)

    mock_post.assert_called_once_with(
        f"/service/{SERVICE_ONE_ID}",
        {
            "created_by": "123",
            "email_message_limit": 250_000,
            "sms_message_limit": 250_000,
            "letter_message_limit": 20_000,
            "messagebox_message_limit": 999_999_999,
            "restricted": False,
            "go_live_at": mocker.ANY,
            "has_active_go_live_request": False,
            **kwargs,
        },
    )
