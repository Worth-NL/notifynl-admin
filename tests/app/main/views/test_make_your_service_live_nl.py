from unittest.mock import PropertyMock

import pytest

from tests.conftest import SERVICE_ONE_ID, create_template, normalize_spaces


@pytest.mark.parametrize(
    "count_of_users_with_manage_service,count_of_invites_with_manage_service,count_of_non_gov_users_with_manage,expected_user_checklist_item",
    [
        (1, 0, 0, "Finish setting up your team Niet voltooid"),
        (1, 1, 0, "Finish setting up your team Niet voltooid"),
        (1, 0, 1, "Finish setting up your team Niet voltooid"),
    ],
)
@pytest.mark.parametrize(
    "count_of_templates, expected_templates_checklist_item",
    [
        (0, "Voeg sjablonen toe met voorbeelden van uw inhoud Niet voltooid"),
        (1, "Voeg sjablonen toe met voorbeelden van uw inhoud Voltooid"),
        (2, "Voeg sjablonen toe met voorbeelden van uw inhoud Voltooid"),
    ],
)
def test_should_check_for_sending_things_right(
    client_request,
    mocker,
    service_one,
    single_sms_sender,
    count_of_users_with_manage_service,
    count_of_invites_with_manage_service,
    count_of_non_gov_users_with_manage,
    expected_user_checklist_item,
    count_of_templates,
    api_nongov_user_active,
    expected_templates_checklist_item,
    active_user_with_permissions,
    active_user_no_settings_permission,
    single_reply_to_email_address,
):
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms") for _ in range(count_of_templates)]},
    )

    mocker.patch(
        "app.organisations_client.get_domains",
        return_value=[],
    )

    mock_get_users = mocker.patch(
        "app.models.user.Users._get_items",
        return_value=(
            [active_user_with_permissions] * count_of_users_with_manage_service
            + [active_user_no_settings_permission]
            + [api_nongov_user_active] * count_of_non_gov_users_with_manage
        ),
    )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Maak uw service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[2].text) == expected_user_checklist_item
    assert normalize_spaces(checklist_items[3].text) == expected_templates_checklist_item

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "count_of_templates, expected_templates_checklist_item",
    [
        (0, "Voeg sjablonen toe met voorbeelden van uw inhoud Niet voltooid"),
        (1, "Voeg sjablonen toe met voorbeelden van uw inhoud Voltooid"),
        (2, "Voeg sjablonen toe met voorbeelden van uw inhoud Voltooid"),
    ],
)
def test_should_check_for_sending_things_right_with_two_gov_users(
    client_request,
    mocker,
    service_one,
    single_sms_sender,
    count_of_templates,
    expected_templates_checklist_item,
    active_user_with_permissions,
    active_user_no_settings_permission,
    single_reply_to_email_address,
):
    # Covers the case skipped in test_make_your_service_live.py::test_should_check_for_sending_things_right
    # (2, 0, 0, "Finish setting up your team Completed") - the [] `get_domains` mock there is
    # upstream-faithful and untouched; the fixture user's email just needs a domain that's
    # actually in email_domains.txt for `is_gov_user`'s static check to resolve True.
    active_user_with_permissions["email_address"] = "test@amsterdam.nl"

    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(template_type="sms") for _ in range(count_of_templates)]},
    )

    mocker.patch(
        "app.organisations_client.get_domains",
        return_value=[],
    )

    mock_get_users = mocker.patch(
        "app.models.user.Users._get_items",
        return_value=[active_user_with_permissions] * 2 + [active_user_no_settings_permission],
    )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Maak uw service live"

    checklist_items = page.select(".govuk-task-list .govuk-task-list__item")
    assert normalize_spaces(checklist_items[2].text) == "Finish setting up your team Voltooid"
    assert normalize_spaces(checklist_items[3].text) == expected_templates_checklist_item

    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


def test_should_not_show_go_live_button_if_service_already_has_active_go_live_request(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_service_organisation,
    mock_get_invites_for_service,
    single_sms_sender,
    single_reply_to_email_address,
):
    mocker.patch(
        "app.models.service.Service.has_active_go_live_request",
        new_callable=PropertyMock,
        return_value=True,
        create=True,
    )
    mocker.patch(
        "app.models.service.Service.go_live_checklist_completed",
        new_callable=PropertyMock,
        return_value=True,
    )
    mocker.patch(
        "app.models.organisation.Organisation.agreement_signed",
        new_callable=PropertyMock,
        return_value=True,
        create=True,
    )

    for channel in ("email", "sms", "letter"):
        mocker.patch(
            f"app.models.service.Service.volume_{channel}",
            create=True,
            new_callable=PropertyMock,
            return_value=0,
        )

    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Maak uw service live"

    assert not page.select("form")
    assert not page.select("form button")
    assert len(page.select("main p")) == 2
    assert normalize_spaces(page.select_one("main p").text) == (
        "You stuurde een verzoek om live te gaan voor deze service."
    )


@pytest.mark.parametrize(
    "go_live_at, message",
    [
        (None, "‘service one’ is al actief."),
        ("2020-10-09 13:55:20", "‘service one’ is actief sinds 9 oktober 2020."),
    ],
)
def test_request_to_go_live_redirects_if_service_already_live(
    client_request,
    service_one,
    go_live_at,
    message,
):
    service_one["restricted"] = False
    service_one["go_live_at"] = go_live_at

    page = client_request.get(
        "main.request_to_go_live",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "Uw dienst is al actief"
    assert normalize_spaces(page.select_one("main p").text) == message


def test_non_gov_user_is_told_they_cant_go_live(
    client_request,
    api_nongov_user_active,
    mocker,
    mock_get_organisations,
    mock_get_organisation,
):
    mocker.patch(
        "app.models.service.Service.has_team_members_with_manage_service_permission",
        return_value=False,
    )
    mocker.patch(
        "app.models.service.Service.all_templates",
        new_callable=PropertyMock,
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_sms_senders",
        return_value=[],
    )
    mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        return_value=[],
    )
    client_request.login(api_nongov_user_active)
    page = client_request.get("main.request_to_go_live", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("main p:last-of-type").text) == (
        "Alleen teamleden met een e -mailadres van de overheid kunnen vragen om live te gaan."
    )
    assert len(page.select("main form")) == 0
    assert len(page.select("main button")) == 0


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Error: Vul een dienstnaam in"),
        (".", "Dienstnaam moet ten minste 2 letters of cijfers bevatten"),
        (
            "GOV.UK Ειδοποίηση",
            "Dienstnaam mag geen niet-latijns alfabet karakters bevatten",
        ),
        (
            "a" * 150 + " " * 100 + "a",
            "Dienstnaam mag niet langer zijn dan 143 karakters",
        ),
    ],
)
def test_confirm_service_is_unique_fails_validation(
    client_request,
    mock_update_service,
    name,
    error_message,
):
    page = client_request.post(
        "main.confirm_service_is_unique",
        service_id=SERVICE_ONE_ID,
        _data={"name": name},
        _expected_status=200,
    )

    assert not mock_update_service.called
    assert error_message in page.select_one(".govuk-error-message").text
