import pytest
from notifications_python_client.errors import HTTPError

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


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
        'E-mailadres,Naam,"Instellingen, team en gebruik beheren",Dashboard bekijken,Berichten versturen,'
        "Sjablonen toevoegen en bewerken,API-integratie beheren,Aanmeldmethode\r\n"
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


@pytest.mark.parametrize(
    "user_is_gov_user, expected_error_msg",
    [
        (
            True,
            (
                "U kunt de rechten van dit teamlid niet wijzigen "
                "Uw dienst heeft ten minste 2 teamleden nodig: "
                "van uw organisatie "
                "met de rechten ‘Instellingen, team en gebruik beheren’ "
                "Voeg nieuwe teamleden toe of werk de rechten van uw team bij en probeer het daarna opnieuw."
            ),
        ),
        (
            False,
            (
                "U kunt de rechten van dit teamlid niet wijzigen "
                "Uw dienst heeft ten minste 2 teamleden nodig: "
                "van een overheidsorganisatie "
                "met de rechten ‘Instellingen, team en gebruik beheren’ "
                "Voeg nieuwe teamleden toe of werk de rechten van uw team bij en probeer het daarna opnieuw."
            ),
        ),
    ],
)
def test_edit_user_permissions_when_api_gives_error_that_permissions_cannot_be_changed(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    mock_get_organisations,
    service_one,
    api_nongov_user_active,
    user_is_gov_user,
    expected_error_msg,
    mocker,
):
    active_user_with_permissions["email_address"] = "test@amsterdam.nl"
    mocker.patch(
        "app.models.user.User.set_permissions",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={
                    "result": "error",
                    "message": "Cannot change user permissions - service would have too few users with manage_settings",
                },
            ),
            message="Cannot change user permissions - service would have too few users with manage_settings",
        ),
    )

    if not user_is_gov_user:
        client_request.login(api_nongov_user_active)
    else:
        client_request.login(active_user_with_permissions)

    page = client_request.post(
        "main.edit_user_permissions",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
        _data={
            "email_address": "test@example.com",
            "manage_service": "y",
        },
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == expected_error_msg


@pytest.mark.parametrize(
    "user_is_gov_user, expected_error_msg",
    [
        (
            True,
            "Uw dienst heeft ten minste 2 teamleden nodig: van uw organisatie",
        ),
        (
            False,
            "Uw dienst heeft ten minste 2 teamleden nodig: van een overheidsorganisatie",
        ),
    ],
)
def test_remove_user_from_service_when_user_api_gives_error_x(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_organisations,
    api_nongov_user_active,
    mock_get_invites_for_service,
    mock_get_template_folders,
    user_is_gov_user,
    expected_error_msg,
    mocker,
):
    active_user_with_permissions["email_address"] = "test@amsterdam.nl"
    mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[active_user_with_permissions, api_nongov_user_active],
    )
    mocker.patch(
        "app.service_api_client.remove_user_from_service",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={
                    "result": "error",
                    "message": "User cannot be removed from the service",
                },
            ),
            message="User cannot be removed from the service",
        ),
    )
    mock_event_handler = mocker.patch("app.main.views_nl.manage_users.Events.remove_user_from_service")

    if not user_is_gov_user:
        client_request.login(api_nongov_user_active)
    else:
        client_request.login(active_user_with_permissions)

    page = client_request.post(
        "main.remove_user_from_service",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
        _follow_redirects=True,
    )
    error_message = normalize_spaces(page.select_one(".banner-dangerous").text)

    assert error_message.startswith("U kunt dit teamlid niet verwijderen")
    assert expected_error_msg in error_message
    assert not mock_event_handler.called
