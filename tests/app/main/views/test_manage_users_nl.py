from tests.conftest import SERVICE_ONE_ID


def test_download_csv_of_users(
    client_request,
    mocker,
    mock_get_invites_for_service,
    service_one,
    active_user_view_permissions,
    active_caseworking_user,
):
    mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[active_user_view_permissions, active_caseworking_user],
    )

    response = client_request.get_response("main.manage_users_download", service_id=SERVICE_ONE_ID)

    assert response.get_data(as_text=True) == (
        'E-mailadres,Naam,"Manage settings, team and usage",See dashboard,Send messages,Add and edit templates,Manage API integration,Aanmeldmethode\r\n'  # noqa: E501
        "caseworker@example.gov.uk,Test User,Nee,Nee,Ja,Nee,Nee,SMS-code\r\n"
        "test@user.gov.uk,Test User With Permissions,Nee,Ja,Nee,Nee,Nee,SMS-code\r\n"
        "user_0@testnotify.gov.uk,(uitgenodigd),Ja,Ja,Ja,Nee,Ja,SMS-code\r\n"
        "user_1@testnotify.gov.uk,(uitgenodigd),Ja,Ja,Ja,Nee,Ja,SMS-code\r\n"
        "user_2@testnotify.gov.uk,(uitgenodigd),Ja,Ja,Ja,Nee,Ja,SMS-code\r\n"
        "user_3@testnotify.gov.uk,(uitgenodigd),Ja,Ja,Ja,Nee,Ja,SMS-code\r\n"
        "user_4@testnotify.gov.uk,(uitgenodigd),Ja,Ja,Ja,Nee,Ja,SMS-code\r\n"
    )

    client_request.login(active_user_view_permissions)
    client_request.get_response(
        "main.manage_users_download",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
    )
