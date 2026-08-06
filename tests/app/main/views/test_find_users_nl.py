from notifications_python_client.errors import HTTPError

from tests.conftest import normalize_spaces


def test_archive_user_prompts_for_confirmation(
    client_request,
    platform_admin_user,
    api_user_active,
    mock_get_organisations_and_services_for_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.archive_user", user_id=api_user_active["id"])

    assert "Weet u zeker dat u deze gebruiker wilt archiveren?" in page.select_one("div.banner-dangerous").text


def test_archive_user_shows_error_message_if_user_cannot_be_archived(
    client_request,
    platform_admin_user,
    api_user_active,
    mocker,
    mock_get_non_empty_organisations_and_services_for_user,
):
    mocker.patch(
        "app.user_api_client.post",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400,
                json={
                    "result": "error",
                    "message": "User cannot be removed from a service",
                },
            ),
            message="User cannot be removed from a service",
        ),
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.archive_user",
        user_id=api_user_active["id"],
        _follow_redirects=True,
    )

    assert (
        "U kunt deze gebruiker niet archiveren "
        "Deze gebruiker heeft voor ten minste één dienst de rechten om instellingen te beheren."
    ) in normalize_spaces(page.select_one(".banner-dangerous").text)
