from unittest.mock import call

import pytest

from tests import find_element_by_tag_and_partial_text, organisation_json, sample_uuid
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_user_no_settings_permission,
    create_active_user_with_permissions,
    create_platform_admin_user,
    create_reply_to_email_address,
    normalize_spaces,
)


def test_should_show_service_name_content(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type=None),
    )

    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Wijzig uw dienstnaam"
    assert "Kies een naam die het NotifyNL-team duidelijk zal begrijpen." in page.select_one("main").text
    assert "acroniemen, initialen of afkortingen" in page.select_one("ul.govuk-list.govuk-list--bullet").text
    assert "uw eigen naam of de naam van iemand in uw team" in page.select_one("ul.govuk-list.govuk-list--bullet").text


@pytest.mark.parametrize(
    "sender_list_page, index, expected_output",
    [
        ("main.service_email_reply_to", 0, "test@example.com (standaard) Wijzigen test@example.com"),
        ("main.service_letter_contact_details", 1, "1 Example Street (standaard) Wijzigen 1 Example Street"),
        ("main.service_sms_senders", 0, "GOVUK (default) Wijzigen GOVUK"),
    ],
)
def test_api_ids_dont_show_on_option_pages_with_a_single_sender(
    client_request,
    single_reply_to_email_address,
    single_letter_contact_block,
    mock_get_organisation,
    single_sms_sender,
    sender_list_page,
    index,
    expected_output,
):
    rows = client_request.get(sender_list_page, service_id=SERVICE_ONE_ID).select(".user-list-item")

    assert normalize_spaces(rows[index].text) == expected_output
    assert len(rows) == index + 1


@pytest.mark.parametrize(
    "initial_permissions, expected_html_element, confirmed_email_sender_name, has_email_reply_to_address",
    [
        (["email", "sms"], ".govuk-radios", None, None),
        (["sms"], ".govuk-task-list", False, False),
        (["sms"], ".govuk-task-list", True, False),
        (["sms"], ".govuk-task-list", False, True),
        (["sms"], ".govuk-task-list", True, True),
    ],
)
def test_set_email_page_markup(
    client_request,
    service_one,
    mocker,
    single_sms_sender,
    api_user_active,
    mock_get_free_sms_fragment_limit,
    mock_get_letter_rates,
    mock_get_sms_rate,
    initial_permissions,
    expected_html_element,
    confirmed_email_sender_name,
    has_email_reply_to_address,
):
    if has_email_reply_to_address:
        mocker.patch(
            "app.service_api_client.get_reply_to_email_addresses",
            return_value=[create_reply_to_email_address(is_default=True)],
        )
    else:
        mocker.patch("app.service_api_client.get_reply_to_email_addresses", return_value=[])
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    service_one["permissions"] = initial_permissions
    service_one["confirmed_email_sender_name"] = confirmed_email_sender_name

    page = client_request.get(
        "main.service_set_channel",
        service_id=service_one["id"],
        channel="email",
    )

    if not confirmed_email_sender_name and "email" not in initial_permissions:
        assert (
            normalize_spaces(
                find_element_by_tag_and_partial_text(
                    page, tag=".govuk-task-list__item", string="Kies een ‘van’ naam"
                ).text
            )
            == "Kies een ‘van’ naam Niet voltooid"
        )
    if not has_email_reply_to_address and "email" not in initial_permissions:
        assert (
            normalize_spaces(
                find_element_by_tag_and_partial_text(
                    page, tag=".govuk-task-list__item", string="Voeg een antwoord-naar-e-mailadres toe"
                ).text
            )
            == "Voeg een antwoord-naar-e-mailadres toe Niet voltooid"
        )
    if has_email_reply_to_address and confirmed_email_sender_name:
        assert (
            normalize_spaces(
                find_element_by_tag_and_partial_text(
                    page, tag=".govuk-task-list__item", string="Voeg een antwoord-naar-e-mailadres toe"
                ).text
            )
            == "Voeg een antwoord-naar-e-mailadres toe Voltooid"
        )
        assert (
            normalize_spaces(
                find_element_by_tag_and_partial_text(
                    page, tag=".govuk-task-list__item", string="Kies een ‘van’ naam"
                ).text
            )
            == "Kies een ‘van’ naam Voltooid"
        )

    assert len(page.select(expected_html_element)) == 1


@pytest.mark.parametrize(
    (
        "initial_permissions,"
        "confirmed_email_sender_name,"
        "has_email_reply_to_address,"
        "expected_updated_permissions,"
        "expected_page_title"
    ),
    [
        (["sms"], False, False, ["sms"], "E-mails versturen"),
        (["sms"], True, False, ["sms"], "E-mails versturen"),
        (["sms"], False, True, ["sms"], "E-mails versturen"),
        (["sms"], True, True, ["sms", "email"], "Instellingen"),
    ],
)
def test_switch_email_on_from_tasklist_form(
    client_request,
    service_one,
    mocker,
    single_sms_sender,
    api_user_active,
    mock_get_free_sms_fragment_limit,
    mock_get_letter_rates,
    mock_get_sms_rate,
    mock_get_service_settings_page_common,
    initial_permissions,
    has_email_reply_to_address,
    confirmed_email_sender_name,
    expected_updated_permissions,
    expected_page_title,
):
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    if has_email_reply_to_address:
        mocker.patch(
            "app.service_api_client.get_reply_to_email_addresses",
            return_value=[create_reply_to_email_address(is_default=True)],
        )
    else:
        mocker.patch(
            "app.service_api_client.get_reply_to_email_addresses",
            return_value=[],
        )

    service_one["permissions"] = initial_permissions
    service_one["confirmed_email_sender_name"] = confirmed_email_sender_name

    mock_update_service = mocker.patch("app.service_api_client.update_service", return_value=service_one)

    page = client_request.post("main.enable_email_channel", service_id=service_one["id"], _follow_redirects=True)

    if not confirmed_email_sender_name or not has_email_reply_to_address:
        assert normalize_spaces(page.select_one(".banner-dangerous h2").text) == ("There is a problem")
        assert normalize_spaces(page.select_one(".banner-dangerous p").text) == (
            "Some of the tasks on this page are incomplete"
        )
    if has_email_reply_to_address and confirmed_email_sender_name:
        assert set(mock_update_service.call_args[1]["permissions"]) == set(expected_updated_permissions)
    else:
        assert not mock_update_service.called

    assert normalize_spaces(page.select_one("h1").text) == expected_page_title


def test_send_files_by_email_in_page_guidance(client_request):
    page = client_request.get("main.send_files_by_email_contact_details", service_id=SERVICE_ONE_ID)
    assert [normalize_spaces(p.text) for p in page.select("main p, main li")] == [
        "Om een bestand per e-mail te versturen, kunt u:",
        "een sjabloon kiezen en ‘Bestanden bijvoegen’ selecteren",
        "of de instructies volgen in onze API-documentatie",
        "U moet contactgegevens voor uw dienst toevoegen zodat uw gebruikers contact kunnen opnemen bij "
        "problemen. Bijvoorbeeld wanneer de link om het bestand te downloaden is verlopen.",
    ]


@pytest.mark.parametrize(
    "user, is_trial_service",
    (
        [create_platform_admin_user(), True],
        [create_platform_admin_user(), False],
        [create_active_user_with_permissions(), True],
        pytest.param(create_active_user_with_permissions(), False, marks=pytest.mark.xfail),
        pytest.param(create_active_user_no_settings_permission(), True, marks=pytest.mark.xfail),
    ),
)
def test_archive_service_after_confirm(
    client_request,
    mocker,
    mock_get_organisations,
    mock_get_organisation_by_domain,
    mock_get_service_and_organisation_counts,
    mock_get_organisations_and_services_for_user,
    mock_get_users_by_service,
    mock_get_service_templates,
    service_one,
    user,
    is_trial_service,
):
    service_one["restricted"] = is_trial_service
    mock_api = mocker.patch("app.service_api_client.post")
    mock_event = mocker.patch("app.main.views_nl.service_settings.index.Events.archive_service")
    redis_delete_mock = mocker.patch("app.notify_client.service_api_client.redis_client.delete")
    mocker.patch("app.notify_client.service_api_client.redis_client.delete_by_pattern")

    client_request.login(user)
    page = client_request.post(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_api.assert_called_once_with(f"/service/{SERVICE_ONE_ID}/archive", data=None)
    mock_event.assert_called_once_with(service_id=SERVICE_ONE_ID, archived_by_id=user["id"])

    assert normalize_spaces(page.select_one("h1").text) == "Uw services"
    assert normalize_spaces(page.select_one(".banner-default-with-tick").text) == "‘service one’ is verwijderd"
    # The one user which is part of this service has the sample_uuid as it's user ID
    assert call(f"user-{sample_uuid()}") in redis_delete_mock.call_args_list


def test_show_sms_prefixing_setting_page(
    client_request,
    mock_update_service,
):
    page = client_request.get("main.service_set_sms_prefix", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one("h1")) == "Sms-berichten starten met servicenaam"
    assert normalize_spaces(page.select_one(".govuk-hint").text) == "Start alle sms-berichten met ‘service one:’"
    radios = page.select("input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "True"
    assert radios[0]["checked"] == ""
    assert radios[1]["value"] == "False"
    with pytest.raises(KeyError):
        assert radios[1]["checked"]


# email sender change page preview contains html so instead of repeatably
# writing out the html in each expected output
# this helper method returns the html with input values
def expected_html_response(input, safe_input_local_part):
    return f"""
        <dl class="govuk-summary-list govuk-summary-list--no-border">
            <div class="govuk-summary-list__row">
            <dt class="govuk-summary-list__key"> Van </dt>
            <dd class="govuk-summary-list__value">
                <span class="govuk-!-display-block govuk-!-margin-bottom-2">{input}</span>
                <span>{safe_input_local_part}@notifynl.nl</span>
            </dd>
            </div>
        </dl>
        """


@pytest.mark.parametrize(
    "expected_preview",
    [
        expected_html_response("service one", "service.one"),
    ],
)
def test_service_preview_email_sender_name_service_name(client_request, expected_preview):
    response = client_request.post_response(
        "main.service_email_sender_preview",
        service_id=SERVICE_ONE_ID,
        _data={"use_custom_email_sender_name": False},
        _expected_status=200,
    )
    assert normalize_spaces(response.get_json()["html"]) == normalize_spaces(expected_preview)


def test_view_edit_service_billing_details(
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_service_billing_details",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text == "Wijzig factuurgegevens"
    assert [label.text.strip() for label in page.select("label.govuk-label")] == [
        "Contact namen",
        "E-mailadressen voor contact",
        "Referentie",
        "Inkoopordernummer",
        "Aantekeningen",
    ]
    assert [
        form_element["name"]
        for form_element in page.select("input.govuk-input.govuk-\\!-width-full") + page.select("textarea")
    ] == [
        "billing_contact_names",
        "billing_contact_email_addresses",
        "billing_reference",
        "purchase_order_number",
        "notes",
    ]
