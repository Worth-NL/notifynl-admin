import pytest
from flask import url_for
from freezegun import freeze_time

from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, _template


@pytest.mark.parametrize(
    "query_args, post_data, expected_arguments_to_update_service, should_notify",
    (
        (
            {"name": "ok", "unique": "yes"},
            {"enabled": True},
            {
                "email_message_limit": 250_000,
                "sms_message_limit": 250_000,
                "letter_message_limit": 20_000,
                "messagebox_message_limit": 999_999_999,
                "restricted": False,
                "go_live_at": "2022-12-22 12:12:12",
                "has_active_go_live_request": False,
            },
            False,
        ),
        (
            {"name": "ok", "unique": "yes"},
            {"enabled": False, "rejection_reason": "It's a stinker"},
            {
                "email_message_limit": 50,
                "sms_message_limit": 50,
                "letter_message_limit": 50,
                "messagebox_message_limit": 50,
                "restricted": True,
                "go_live_at": None,
                "has_active_go_live_request": False,
            },
            True,
        ),
    ),
)
@freeze_time("2022-12-22 12:12:12")
def test_post_org_member_make_service_live_decision(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_update_service,
    query_args,
    post_data,
    expected_arguments_to_update_service,
    should_notify,
    mocker,
):
    service_one["has_active_go_live_request"] = True
    service_one["organisation"] = ORGANISATION_ID
    service_one["permissions"] = ["sms", "email", "letter"]
    service_one["volume_email"] = 2000

    templates = [
        _template(template_type, f"Template {index}") for index, template_type in enumerate(["sms", "email", "letter"])
    ]
    mocker.patch("app.service_api_client.get_service_templates", return_value={"data": templates})

    mock_notify = mocker.patch("app.organisations_client.notify_service_member_of_rejected_go_live_request")

    client_request.login(platform_admin_user)

    client_request.post(
        "main.org_member_make_service_live_decision",
        service_id=SERVICE_ONE_ID,
        **query_args,
        _data=post_data,
        _expected_redirect=url_for("main.organisation_dashboard", org_id=ORGANISATION_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        **expected_arguments_to_update_service,
    )

    if should_notify:
        assert mock_notify.call_args_list == [
            mocker.call(
                service_id=service_one["id"],
                service_member_name="Platform admin user",
                service_name="service one",
                organisation_name="Test organisation",
                rejection_reason="It's a stinker",
                organisation_team_member_name="Platform admin user",
                organisation_team_member_email="platform@admin.gov.uk",
            )
        ]
