import re

import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

from tests import organisation_json
from tests.conftest import ORGANISATION_ID, create_user, normalize_spaces, sample_uuid

ENDPOINT_URL = "https://print.example.com/letters"
PINGEN = {
    "organisation_id": ORGANISATION_ID,
    "identifier": "pingen",
    "display_name": "Pingen",
    "endpoint_url": None,
    "auth_method": None,
    "address_placement": "60mm",
    "has_credentials": False,
    "auth_config": {},
    "is_complete": True,
    "updated_at": None,
    "updated_by_id": None,
}
REST_ENDPOINT = PINGEN | {
    "identifier": "rest-endpoint",
    "display_name": "REST-endpoint",
    "endpoint_url": ENDPOINT_URL,
    "auth_method": "basic",
    "address_placement": "50mm",
    "has_credentials": True,
    "auth_config": {"username": "denhaag"},
    "updated_at": "2026-09-29T12:00:00.000000Z",
}
# what notifynl-api's serialize_summary puts in the organisation JSON
SUMMARY_FIELDS = ("identifier", "display_name", "endpoint_url", "auth_method", "address_placement", "has_credentials")
SECRETS = {"password", "api_key", "client_secret"}


@pytest.fixture
def org_member():
    return create_user(id=sample_uuid(), organisations=[ORGANISATION_ID])


@pytest.fixture
def letter_provider(notify_admin, mocker):
    """The organisation's letter provider as notifynl-api returns it: set .return_value to change it."""
    return mocker.patch("app.organisations_client.get_organisation_letter_provider", return_value=PINGEN)


@pytest.fixture
def mock_get_organisation(notify_admin, mocker, letter_provider):
    """Overrides the conftest fixture: the organisation JSON summarises the letter provider it has stored"""

    def _get_organisation(org_id):
        stored = letter_provider.return_value
        summary = {field: stored[field] for field in SUMMARY_FIELDS} if stored else None
        return organisation_json(org_id, "Test organisation", letter_provider=summary)

    return mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)


@pytest.fixture
def mock_set_letter_provider(notify_admin, mocker):
    def _set(org_id, data, cached_service_ids=None):
        if data["provider"] == "pingen":
            return PINGEN
        # like notifynl-api: what was saved, without the secrets
        return REST_ENDPOINT | {
            "endpoint_url": data["endpoint_url"],
            "auth_method": data["auth_method"],
            "auth_config": {name: value for name, value in data["auth_config"].items() if name not in SECRETS},
            "address_placement": data["address_placement"],
        }

    return mocker.patch("app.organisations_client.set_organisation_letter_provider", side_effect=_set)


@pytest.fixture
def organisation_services(notify_admin, mocker):
    return mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[{"id": "service-1", "name": "Dienst 1", "active": True, "restricted": False}],
    )


@pytest.fixture
def logged_in_org_member(client_request, org_member, mock_get_organisation, letter_provider):
    client_request.login(org_member)
    return client_request


def _form_errors(page):
    return [normalize_spaces(error.text) for error in page.select(".govuk-error-message")]


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.organisation_settings",
        "main.organisation_change_letter_provider",
        "main.organisation_letter_endpoint",
    ],
)
def test_any_organisation_member_can_manage_the_letter_provider(logged_in_org_member, endpoint):
    logged_in_org_member.get(endpoint, org_id=ORGANISATION_ID)


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.organisation_settings",
        "main.organisation_change_letter_provider",
        "main.organisation_letter_endpoint",
    ],
)
def test_platform_admins_can_manage_the_letter_provider(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_empty_email_branding_pool,
    mock_get_empty_letter_branding_pool,
    letter_provider,
    endpoint,
):
    client_request.login(platform_admin_user)
    client_request.get(endpoint, org_id=ORGANISATION_ID)


@pytest.mark.parametrize(
    "endpoint, method",
    [
        ("main.organisation_settings", "get"),
        ("main.organisation_change_letter_provider", "post"),
        ("main.organisation_confirm_pingen_letter_provider", "post"),
        ("main.organisation_letter_endpoint", "post"),
    ],
)
def test_other_users_cannot_manage_the_letter_provider(
    client_request, mock_get_organisation, letter_provider, mock_set_letter_provider, endpoint, method
):
    letter_provider.return_value = REST_ENDPOINT
    client_request.login(create_user(id=sample_uuid(), organisations=[sample_uuid()]))

    getattr(client_request, method)(endpoint, org_id=ORGANISATION_ID, _expected_status=403)

    assert not mock_set_letter_provider.called


def test_organisation_members_see_only_the_letter_provider_in_the_settings(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_settings", org_id=ORGANISATION_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Instellingen"
    keys = [normalize_spaces(key.text) for key in page.select(".govuk-summary-list__key")]
    assert keys == ["Printleverancier", "Adres op de brief"]
    assert not page.select_one("a[href$='/settings/archive']")


def test_platform_admins_see_every_organisation_setting_and_then_the_letter_provider(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mock_get_empty_email_branding_pool,
    mock_get_empty_letter_branding_pool,
):
    client_request.login(platform_admin_user)

    page = client_request.get("main.organisation_settings", org_id=ORGANISATION_ID)

    keys = [normalize_spaces(key.text) for key in page.select(".govuk-summary-list__key")]
    assert keys[0] == "Naam"
    assert keys[-3:] == ["Gebiedsgrens", "Printleverancier", "Adres op de brief"]
    assert page.select_one("a[href$='/settings/archive']")


def test_every_other_organisation_setting_stays_platform_admin_only(notify_admin, logged_in_org_member):
    other_settings = [
        rule.rule.replace("<uuid:org_id>", ORGANISATION_ID)
        for rule in notify_admin.url_map.iter_rules()
        if rule.rule.startswith("/organisations/<uuid:org_id>/settings/")
        and rule.rule != "/organisations/<uuid:org_id>/settings/"
    ]
    assert len(other_settings) >= 15

    for url in other_settings:
        logged_in_org_member.get_url(url, _expected_status=403)


def test_organisation_nav_shows_instellingen_to_organisation_members(logged_in_org_member, mocker):
    mocker.patch("app.organisations_client.get_services_and_usage", return_value={"services": [], "updated_at": None})

    page = logged_in_org_member.get("main.organisation_change_letter_provider", org_id=ORGANISATION_ID)

    nav_items = [normalize_spaces(item.text) for item in page.select("nav.navigation a")]
    assert nav_items == ["Gebruik", "Teamleden", "Instellingen"]
    assert "selected" in page.select_one("nav.navigation a[href$='/settings/']")["class"]


@pytest.mark.parametrize("pingen", [PINGEN, None])
def test_letter_provider_page_for_pingen(logged_in_org_member, letter_provider, pingen):
    letter_provider.return_value = pingen

    page = logged_in_org_member.get("main.organisation_settings", org_id=ORGANISATION_ID)

    rows = [normalize_spaces(row.text) for row in page.select(".govuk-summary-list__row")]
    assert rows == [
        "Printleverancier Pingen Wijzigen printleverancier",
        "Adres op de brief 60 mm vanaf de bovenkant (vast bij Pingen)",
    ]
    assert not page.select(".govuk-warning-text")
    # nothing stored, nothing to fetch: the organisation JSON already says so
    assert letter_provider.called is bool(pingen)


def test_letter_provider_page_for_a_rest_endpoint(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.get("main.organisation_settings", org_id=ORGANISATION_ID)

    rows = [
        normalize_spaces(row.select_one(".govuk-summary-list__key").text)
        + ": "
        + normalize_spaces(row.select_one(".govuk-summary-list__value").text)
        for row in page.select(".govuk-summary-list__row")
    ]
    assert rows == [
        "Printleverancier: Eigen printleverancier",
        f"Endpoint-URL: {ENDPOINT_URL}",
        "Inlogmethode: Gebruikersnaam en wachtwoord (Basic)",
        "Gebruikersnaam: denhaag",
        "Inloggegevens: Opgeslagen",
        "Adres op de brief: 50 mm vanaf de bovenkant",
    ]
    assert not page.select(".govuk-warning-text")
    assert "mutual TLS" in normalize_spaces(page.select_one(".govuk-inset-text").text)


def test_letter_provider_page_lists_the_login_details_in_form_order(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT | {
        "auth_method": "oauth",
        # alphabetical, as the API's JSON has it
        "auth_config": {"client_id": "notify", "scope": "letters", "token_endpoint": "https://print.example.com/token"},
    }

    page = logged_in_org_member.get("main.organisation_settings", org_id=ORGANISATION_ID)

    keys = [normalize_spaces(key.text) for key in page.select(".govuk-summary-list__key")]
    assert keys[keys.index("Inlogmethode") + 1 : keys.index("Inloggegevens")] == ["Token-URL", "Client-ID", "Scope"]


def test_letter_provider_page_warns_about_an_incomplete_rest_endpoint(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT | {"has_credentials": False, "is_complete": False}

    page = logged_in_org_member.get("main.organisation_settings", org_id=ORGANISATION_ID)

    warning = normalize_spaces(page.select_one(".govuk-warning-text").text)
    assert "stuurt NotifyNL uw brieven naar Pingen" in warning
    # where notifynl-api validates the address until then, whatever the stored endpoint says
    assert "moet het adres op 60 mm vanaf de bovenkant staan" in warning


def test_change_letter_provider_page_warns_about_letters_in_progress(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_change_letter_provider", org_id=ORGANISATION_ID)

    assert page.select_one("input[name=provider][checked]")["value"] == "pingen"
    assert "gaan naar de nieuwe printleverancier" in normalize_spaces(page.select_one(".govuk-warning-text").text)


def test_change_letter_provider_page_shows_the_warnings_between_the_heading_and_the_options(
    logged_in_org_member, letter_provider
):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.get("main.organisation_change_letter_provider", org_id=ORGANISATION_ID)

    hint = page.select_one("fieldset .govuk-hint")
    assert len(hint.select(".govuk-warning-text")) == 2
    assert hint.find_previous("h1")
    assert hint.find_next(class_="govuk-radios__item")
    assert hint["id"] in page.select_one("fieldset")["aria-describedby"]


def test_choosing_a_rest_endpoint_goes_to_its_settings(logged_in_org_member, mock_set_letter_provider):
    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "rest-endpoint"},
        _expected_redirect=url_for("main.organisation_letter_endpoint", org_id=ORGANISATION_ID),
    )

    assert not mock_set_letter_provider.called


@pytest.mark.parametrize("stored, expected_warning", [(REST_ENDPOINT, True), (PINGEN, False), (None, False)])
def test_change_letter_provider_page_warns_that_pingen_deletes_a_stored_endpoint(
    logged_in_org_member, letter_provider, stored, expected_warning
):
    letter_provider.return_value = stored

    page = logged_in_org_member.get("main.organisation_change_letter_provider", org_id=ORGANISATION_ID)

    warnings = [normalize_spaces(warning.text) for warning in page.select(".govuk-warning-text")]
    assert any("verwijdert NotifyNL de instellingen en inloggegevens" in warning for warning in warnings) is (
        expected_warning
    )


def test_choosing_pingen_with_a_stored_rest_endpoint_asks_first(
    logged_in_org_member, letter_provider, mock_set_letter_provider, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "pingen"},
        _expected_redirect=url_for("main.organisation_confirm_pingen_letter_provider", org_id=ORGANISATION_ID),
    )

    assert not mock_set_letter_provider.called
    assert not mock_events.called


def test_confirm_pingen_page_asks_before_deleting_the_rest_endpoint(
    logged_in_org_member, letter_provider, mock_set_letter_provider
):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.get("main.organisation_confirm_pingen_letter_provider", org_id=ORGANISATION_ID)

    banner = page.select_one(".banner-dangerous")
    assert "verwijdert dan de instellingen en inloggegevens van uw eigen printleverancier" in normalize_spaces(
        banner.text
    )
    assert normalize_spaces(banner.select_one("button").text) == "Ja, verwijderen"
    assert banner.select_one("form")["action"] == url_for(
        "main.organisation_confirm_pingen_letter_provider", org_id=ORGANISATION_ID
    )
    # the settings below it still show the endpoint that would be deleted
    assert ENDPOINT_URL in normalize_spaces(page.select_one(".govuk-summary-list").text)
    assert not mock_set_letter_provider.called


@pytest.mark.parametrize("stored", [PINGEN, None])
@pytest.mark.parametrize("method", ["get", "post"])
def test_confirm_pingen_page_without_a_stored_rest_endpoint_goes_back(
    logged_in_org_member, letter_provider, mock_set_letter_provider, stored, method
):
    letter_provider.return_value = stored

    getattr(logged_in_org_member, method)(
        "main.organisation_confirm_pingen_letter_provider",
        org_id=ORGANISATION_ID,
        _expected_redirect=url_for("main.organisation_change_letter_provider", org_id=ORGANISATION_ID),
    )

    assert not mock_set_letter_provider.called


def test_choosing_pingen_without_a_stored_letter_provider_saves_it(
    logged_in_org_member, org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = None

    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "pingen"},
        _expected_redirect=url_for("main.organisation_settings", org_id=ORGANISATION_ID),
    )

    mock_set_letter_provider.assert_called_once_with(
        ORGANISATION_ID, {"provider": "pingen", "updated_by_id": org_member["id"]}, cached_service_ids=["service-1"]
    )
    assert mock_events.called


def test_confirming_pingen_saves_it_and_logs_an_event(
    logged_in_org_member, org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    logged_in_org_member.post(
        "main.organisation_confirm_pingen_letter_provider",
        org_id=ORGANISATION_ID,
        _expected_redirect=url_for("main.organisation_settings", org_id=ORGANISATION_ID),
    )

    mock_set_letter_provider.assert_called_once_with(
        ORGANISATION_ID, {"provider": "pingen", "updated_by_id": org_member["id"]}, cached_service_ids=["service-1"]
    )
    event_type, event_data = mock_events.call_args.args
    assert event_type == "update_organisation_letter_provider"
    assert {key: value for key, value in event_data.items() if key not in {"ip_address", "browser_fingerprint"}} == {
        "organisation_id": ORGANISATION_ID,
        "updated_by_id": org_member["id"],
        "old_provider": "rest-endpoint",
        "new_provider": "pingen",
        "old_endpoint_url": ENDPOINT_URL,
        "new_endpoint_url": None,
        "old_auth_method": "basic",
        "new_auth_method": None,
        "old_auth_config": {"username": "denhaag"},
        "new_auth_config": {},
        "old_address_placement": "50mm",
        "new_address_placement": "60mm",
        "credentials_entered": False,
    }


def test_choosing_pingen_again_changes_nothing(logged_in_org_member, mock_set_letter_provider, mock_events):
    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "pingen"},
        _expected_redirect=url_for("main.organisation_settings", org_id=ORGANISATION_ID),
    )

    assert not mock_set_letter_provider.called
    assert not mock_events.called


def test_rest_endpoint_page_never_shows_stored_secrets(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.get("main.organisation_letter_endpoint", org_id=ORGANISATION_ID)

    assert page.select_one("input[name=endpoint_url]")["value"] == ENDPOINT_URL
    assert page.select_one("input[name=auth_method][checked]")["value"] == "basic"
    assert page.select_one("input[name=username]")["value"] == "denhaag"
    # a placeholder instead of the stored password, which the API never returns anyway
    assert page.select_one("input[name=password]")["value"] == "secret_set"
    assert page.select_one("input[name=password]")["type"] == "password"
    assert "Als u een URL wijzigt, moet u dit opnieuw invullen" in normalize_spaces(page.text)


@pytest.mark.parametrize("stored", [REST_ENDPOINT, PINGEN])
def test_rest_endpoint_page_keeps_the_browser_from_filling_in_a_saved_login(
    logged_in_org_member, letter_provider, stored
):
    letter_provider.return_value = stored

    page = logged_in_org_member.get("main.organisation_letter_endpoint", org_id=ORGANISATION_ID)

    inputs = page.select("main form input[type=text], main form input[type=password]")
    assert {field["name"]: field.get("autocomplete") for field in inputs} == {
        "endpoint_url": "off",
        "username": "off",
        "password": "new-password",
        "api_key_header": "off",
        "api_key": "new-password",
        "token_endpoint": "off",
        "client_id": "off",
        "client_secret": "new-password",
        "scope": "off",
    }


def test_rest_endpoint_page_for_an_organisation_on_pingen(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_letter_endpoint", org_id=ORGANISATION_ID)

    assert not page.select_one("input[name=endpoint_url]").get("value")
    assert not page.select_one("input[name=password]").get("value")
    assert page.select_one("input[name=api_key_header]")["value"] == "X-Api-Key"
    assert page.select_one("input[name=address_placement][checked]")["value"] == "50mm"


@pytest.mark.parametrize(
    "form_data, expected_auth_config",
    [
        (
            {"auth_method": "basic", "username": "denhaag", "password": "hunter2"},
            {"username": "denhaag", "password": "hunter2"},
        ),
        (
            {"auth_method": "api_key", "api_key_header": "Ocp-Apim-Subscription-Key", "api_key": "k3y"},
            {"api_key_header": "Ocp-Apim-Subscription-Key", "api_key": "k3y"},
        ),
        (
            {
                "auth_method": "oauth",
                "token_endpoint": "https://login.example.com/token",
                "client_id": "notify",
                "client_secret": "s3cret",
                "scope": "",
            },
            {
                "token_endpoint": "https://login.example.com/token",
                "client_id": "notify",
                "client_secret": "s3cret",
                "scope": "",
            },
        ),
    ],
)
def test_saving_a_rest_endpoint(
    logged_in_org_member,
    org_member,
    mock_set_letter_provider,
    organisation_services,
    mock_events,
    form_data,
    expected_auth_config,
):
    logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={"endpoint_url": ENDPOINT_URL, "address_placement": "50mm"} | form_data,
        _expected_redirect=url_for("main.organisation_settings", org_id=ORGANISATION_ID),
    )

    mock_set_letter_provider.assert_called_once_with(
        ORGANISATION_ID,
        {
            "provider": "rest-endpoint",
            "endpoint_url": ENDPOINT_URL,
            "auth_method": form_data["auth_method"],
            "auth_config": expected_auth_config,
            "address_placement": "50mm",
            "updated_by_id": org_member["id"],
        },
        cached_service_ids=["service-1"],
    )
    _, event_data = mock_events.call_args.args
    assert (event_data["old_provider"], event_data["new_provider"]) == ("pingen", "rest-endpoint")
    assert (event_data["old_endpoint_url"], event_data["new_endpoint_url"]) == (None, ENDPOINT_URL)
    assert (event_data["old_auth_method"], event_data["new_auth_method"]) == (None, form_data["auth_method"])
    assert event_data["new_auth_config"] == {
        name: value for name, value in expected_auth_config.items() if name not in SECRETS
    }
    assert event_data["credentials_entered"] is True
    # never any credentials in the audit event
    assert not {"auth_config", *SECRETS} & set(event_data)
    assert not any(secret in str(event_data) for secret in ("hunter2", "k3y", "s3cret"))


def _event_changes(mock_events):
    """The old and new value of every letter provider setting that the event says changed"""
    _, event_data = mock_events.call_args.args
    return {
        key.removeprefix("new_"): (event_data[f"old_{key.removeprefix('new_')}"], value)
        for key, value in event_data.items()
        if key.startswith("new_") and event_data[f"old_{key.removeprefix('new_')}"] != value
    }


def test_saving_a_rest_endpoint_logs_a_changed_address_placement(
    logged_in_org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={
            "endpoint_url": ENDPOINT_URL,
            "address_placement": "60mm",
            "auth_method": "basic",
            "username": "denhaag",
            "password": "secret_set",
        },
        _expected_status=302,
    )

    assert _event_changes(mock_events) == {"address_placement": ("50mm", "60mm")}
    assert mock_events.call_args.args[1]["credentials_entered"] is False


def test_saving_an_oauth_endpoint_logs_a_changed_token_url(
    logged_in_org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT | {
        "auth_method": "oauth",
        "auth_config": {"token_endpoint": "https://login.example.com/token", "client_id": "notify"},
    }

    logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={
            "endpoint_url": ENDPOINT_URL,
            "address_placement": "50mm",
            "auth_method": "oauth",
            "token_endpoint": "https://elsewhere.example.com/token",
            "client_id": "notify",
            "client_secret": "n3w-s3cret",
            "scope": "",
        },
        _expected_status=302,
    )

    assert _event_changes(mock_events) == {
        "auth_config": (
            {"token_endpoint": "https://login.example.com/token", "client_id": "notify"},
            {"token_endpoint": "https://elsewhere.example.com/token", "client_id": "notify", "scope": ""},
        )
    }
    assert mock_events.call_args.args[1]["credentials_entered"] is True
    assert "n3w-s3cret" not in str(mock_events.call_args.args[1])


def test_letter_provider_event_leaves_out_secrets_even_if_the_api_returned_them(
    logged_in_org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT | {"auth_config": {"username": "denhaag", "password": "hunter2"}}

    logged_in_org_member.post("main.organisation_confirm_pingen_letter_provider", org_id=ORGANISATION_ID)

    assert mock_events.call_args.args[1]["old_auth_config"] == {"username": "denhaag"}
    assert "hunter2" not in str(mock_events.call_args.args[1])


def test_saving_a_rest_endpoint_keeps_the_stored_secret_when_it_is_left_as_is(
    logged_in_org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={
            "endpoint_url": ENDPOINT_URL,
            "address_placement": "60mm",
            "auth_method": "basic",
            "username": "denhaag",
            "password": "secret_set",
        },
        _expected_status=302,
    )

    (_, data), _ = mock_set_letter_provider.call_args
    # empty: the API keeps the stored password
    assert data["auth_config"] == {"username": "denhaag", "password": ""}
    assert data["address_placement"] == "60mm"


@pytest.mark.parametrize(
    "changed",
    [
        {"endpoint_url": "https://attacker.example.net/letters"},
        {"auth_method": "api_key", "api_key_header": "X-Api-Key", "api_key": "secret_set"},
    ],
)
def test_saving_a_rest_endpoint_requires_the_secret_again_when_its_destination_changes(
    logged_in_org_member, letter_provider, mock_set_letter_provider, changed
):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={
            "endpoint_url": ENDPOINT_URL,
            "address_placement": "50mm",
            "auth_method": "basic",
            "username": "denhaag",
            "password": "secret_set",
        }
        | changed,
        _expected_status=200,
    )

    assert any("opnieuw in" in error for error in _form_errors(page))
    assert not mock_set_letter_provider.called


def test_saving_an_oauth_endpoint_requires_the_client_secret_again_when_the_token_url_changes(
    logged_in_org_member, letter_provider, mock_set_letter_provider
):
    letter_provider.return_value = REST_ENDPOINT | {
        "auth_method": "oauth",
        "auth_config": {"token_endpoint": "https://login.example.com/token", "client_id": "notify", "scope": None},
    }

    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={
            "endpoint_url": ENDPOINT_URL,
            "address_placement": "50mm",
            "auth_method": "oauth",
            "token_endpoint": "https://attacker.example.net/token",
            "client_id": "notify",
            "client_secret": "secret_set",
        },
        _expected_status=200,
    )

    assert _form_errors(page) == [
        "Error: Vul het client secret opnieuw in: inloggegevens worden niet bewaard als een URL verandert"
    ]
    assert not mock_set_letter_provider.called


@pytest.mark.parametrize(
    "form_data, expected_errors",
    [
        ({"auth_method": "basic"}, ["Error: Vul de gebruikersnaam in", "Error: Vul het wachtwoord in"]),
        (
            {"auth_method": "api_key", "api_key_header": "", "api_key": ""},
            ["Error: Vul de naam van de header in", "Error: Vul de API-sleutel in"],
        ),
        (
            {"auth_method": "oauth", "client_id": "notify", "client_secret": "s"},
            ["Error: Vul de token-URL in"],
        ),
        (
            {"auth_method": "api_key", "api_key_header": "X Api Key", "api_key": "k"},
            ["Error: Deze naam kan niet als header worden gebruikt"],
        ),
        (
            {"auth_method": "api_key", "api_key_header": "Host", "api_key": "k"},
            ["Error: Deze naam kan niet als header worden gebruikt"],
        ),
        (
            {"endpoint_url": "http://print.example.com/letters", "auth_method": "api_key", "api_key": "k"},
            ["Error: Het adres moet met https:// beginnen"],
        ),
        (
            {"endpoint_url": "", "auth_method": "api_key", "api_key": "k"},
            ["Error: Vul de endpoint-URL in"],
        ),
        (
            {
                "auth_method": "oauth",
                "token_endpoint": "http://login.example.com/token",
                "client_id": "n",
                "client_secret": "s",
            },
            ["Error: Het adres moet met https:// beginnen"],
        ),
        ({}, ["Error: Selecteer hoe NotifyNL inlogt"]),
    ],
)
def test_saving_a_rest_endpoint_validates_it(
    logged_in_org_member, mock_set_letter_provider, form_data, expected_errors
):
    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={"endpoint_url": ENDPOINT_URL, "address_placement": "50mm"} | form_data,
        _expected_status=200,
    )

    assert _form_errors(page) == expected_errors
    assert not mock_set_letter_provider.called


def test_saving_a_rest_endpoint_allows_http_for_local_development(
    notify_admin, logged_in_org_member, mock_set_letter_provider, organisation_services, mock_events
):
    notify_admin.config["LETTER_ENDPOINT_ALLOW_INSECURE"] = True
    try:
        logged_in_org_member.post(
            "main.organisation_letter_endpoint",
            org_id=ORGANISATION_ID,
            _data={
                "endpoint_url": "http://localhost:6300/letter-endpoint",
                "address_placement": "50mm",
                "auth_method": "api_key",
                "api_key": "k",
            },
            _expected_status=302,
        )
    finally:
        notify_admin.config.pop("LETTER_ENDPOINT_ALLOW_INSECURE")


@pytest.mark.parametrize(
    "api_message, field, expected_error",
    [
        (
            f"{ENDPOINT_URL} must not point to a private or internal address",
            "endpoint_url",
            "Error: NotifyNL kan dit adres niet gebruiken: het is onbekend of intern",
        ),
        (
            f"The host of {ENDPOINT_URL} cannot be resolved",
            "endpoint_url",
            "Error: NotifyNL kan dit adres niet gebruiken: het is onbekend of intern",
        ),
        (
            "Missing api_key for auth method api_key: credentials have to be entered again when a URL changes",
            "api_key",
            "Error: Vul de API-sleutel opnieuw in: inloggegevens worden niet bewaard als een URL verandert",
        ),
    ],
)
def test_saving_a_rest_endpoint_shows_errors_from_the_api(
    logged_in_org_member, organisation_services, mocker, mock_events, api_message, field, expected_error
):
    response = mocker.Mock(status_code=400, json=lambda: {"result": "error", "message": api_message})
    mocker.patch(
        "app.organisations_client.set_organisation_letter_provider",
        side_effect=HTTPError(response=response, message=api_message),
    )

    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={"endpoint_url": ENDPOINT_URL, "address_placement": "50mm", "auth_method": "api_key", "api_key": "k"},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(f"#{field}-error").text) == expected_error
    assert not mock_events.called


CONNECTION_TEST_ID = "7b2dd5d6-b52f-4a9c-9d0e-9d3b4b1b4a51"
CONNECTION_TEST_FORM = {
    "endpoint_url": ENDPOINT_URL,
    "address_placement": "50mm",
    "auth_method": "basic",
    "username": "denhaag",
    "password": "typed-password",
    "test_connection": "1",
}
NOT_SAVED = "Let op: deze gegevens zijn nog niet opgeslagen."
VALUES_CHANGED = "U hebt de gegevens gewijzigd nadat deze test begon."


def _finished(outcome, **overrides):
    return {
        "state": "finished",
        "outcome": outcome,
        "step": "letter",
        "host": "print.example.com",
        "duration_ms": 5,
        "status_code": 200,
        "reason": "OK",
        "content_type": "application/json",
        "location": None,
        "error": None,
        "timed_out": False,
        "body": '{"id": "job-1"}',
        "body_kind": "text",
        "body_truncated": False,
    } | overrides


@pytest.fixture
def no_waiting(mocker):
    return mocker.patch("app.main.views_nl.organisations.letter_provider.time.sleep")


@pytest.fixture
def start_connection_test(notify_admin, mocker, no_waiting):
    return mocker.patch(
        "app.organisations_client.start_letter_endpoint_connection_test", return_value={"id": CONNECTION_TEST_ID}
    )


@pytest.fixture
def connection_test_result(notify_admin, mocker):
    return mocker.patch(
        "app.organisations_client.get_letter_endpoint_connection_test", return_value=_finished("authorized")
    )


def _test_connection(client_request, data=None, _expected_status=200):
    return client_request.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data=CONNECTION_TEST_FORM | (data or {}),
        _expected_status=_expected_status,
    )


def _buttons(page):
    return [normalize_spaces(button.text) for button in page.select("main form button")]


def test_rest_endpoint_page_has_a_test_button_after_the_save_button(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_letter_endpoint", org_id=ORGANISATION_ID)

    assert _buttons(page) == ["Opslaan", "Verbinding testen"]
    assert page.select_one("button[name=test_connection]")
    assert not page.select_one("#connection-test-result")


def test_rest_endpoint_page_says_the_test_sends_a_letter_that_may_be_printed(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_letter_endpoint", org_id=ORGANISATION_ID)

    assert normalize_spaces(page.select_one("#connection-test-hint").text) == (
        "Met ‘Verbinding testen’ stuurt NotifyNL een testbrief van één pagina zonder adres naar uw printleverancier, "
        "met de gegevens hierboven. Op de brief staat ‘niet afdrukken’, maar uw printleverancier kan hem toch "
        "afdrukken."
    )
    assert page.select_one("button[name=test_connection]")["aria-describedby"] == "connection-test-hint"


def test_testing_the_connection_uses_the_typed_values_and_saves_nothing(
    logged_in_org_member,
    org_member,
    start_connection_test,
    connection_test_result,
    mock_set_letter_provider,
    mock_events,
):
    page = _test_connection(logged_in_org_member)

    start_connection_test.assert_called_once_with(
        ORGANISATION_ID,
        {
            "endpoint_url": ENDPOINT_URL,
            "auth_method": "basic",
            "auth_config": {"username": "denhaag", "password": "typed-password"},
        },
    )
    assert not mock_set_letter_provider.called
    assert NOT_SAVED in normalize_spaces(page.select_one("#connection-test-result").text)
    # so they can be saved straight after
    assert page.select_one("input[name=endpoint_url]")["value"] == ENDPOINT_URL
    assert page.select_one("input[name=password]")["value"] == "typed-password"

    event_type, event_data = mock_events.call_args.args
    assert event_type == "start_letter_endpoint_connection_test"
    assert {key: value for key, value in event_data.items() if key not in {"ip_address", "browser_fingerprint"}} == {
        "organisation_id": ORGANISATION_ID,
        "started_by_id": org_member["id"],
        "connection_test_id": CONNECTION_TEST_ID,
        "endpoint_url": ENDPOINT_URL,
        "token_endpoint": None,
        "auth_method": "basic",
    }


@pytest.mark.parametrize(
    "result, expected_banner, expected_text",
    [
        (
            _finished("authorized"),
            ".banner-default-with-tick",
            "Verbonden en correct geautoriseerd, met dit antwoord:",
        ),
        (
            _finished("connected", status_code=422, reason="Unprocessable Entity"),
            ".banner-default",
            "Verbonden, met dit antwoord:",
        ),
        (
            _finished("connected", status_code=500, reason="Internal Server Error"),
            ".banner-default",
            "Verbonden, met dit antwoord:",
        ),
        (
            _finished("unauthorized", status_code=401, reason="Unauthorized"),
            ".banner-dangerous",
            "Niet geautoriseerd: het endpoint print.example.com heeft de inloggegevens geweigerd.",
        ),
        (
            _finished("unauthorized", step="token", host="idp.example.com", status_code=400, reason="Bad Request"),
            ".banner-dangerous",
            "Niet geautoriseerd: de token-URL idp.example.com heeft de inloggegevens geweigerd.",
        ),
        (
            _finished("unauthorized", step="token", host="idp.example.com", body=None, body_kind="unusable_token"),
            ".banner-dangerous",
            "Niet geautoriseerd: de token-URL idp.example.com gaf geen bruikbaar toegangstoken.",
        ),
        (
            _finished("no_connection", status_code=None, reason="", body=None, error="[Errno 111] Connection refused"),
            ".banner-dangerous",
            "Geen verbinding met print.example.com: [Errno 111] Connection refused",
        ),
        (
            _finished("no_reply", status_code=None, reason="", body=None, error="Read timed out. (read timeout=15)"),
            ".banner-default",
            "Geen antwoord van het endpoint print.example.com. De testbrief kan wel zijn ontvangen. "
            "Read timed out. (read timeout=15)",
        ),
        (
            _finished("no_reply", step="token", host="idp.example.com", status_code=None, body=None, error="Timeout"),
            ".banner-default",
            "Geen antwoord van de token-URL idp.example.com. Er is geen testbrief verstuurd.",
        ),
        (
            _finished("no_reply", status_code=None, reason="", body=None, timed_out=True, duration_ms=59400),
            ".banner-default",
            "Geen antwoord van het endpoint print.example.com. De testbrief kan wel zijn ontvangen. "
            "NotifyNL is na 59 seconden gestopt met wachten op het antwoord.",
        ),
        (
            {"state": "finished", "outcome": "failed"},
            ".banner-default",
            "De test kon niet worden uitgevoerd.",
        ),
    ],
)
def test_the_result_of_a_connection_test(
    logged_in_org_member,
    start_connection_test,
    connection_test_result,
    mock_events,
    result,
    expected_banner,
    expected_text,
):
    connection_test_result.return_value = result

    page = _test_connection(logged_in_org_member)

    banner = page.select_one(f"#connection-test-result {expected_banner}")
    assert expected_text in normalize_spaces(banner.text)
    assert NOT_SAVED in normalize_spaces(page.select_one("#connection-test-result").text)
    assert bool(page.select(".banner-dangerous")) == (expected_banner == ".banner-dangerous")


@pytest.mark.parametrize(
    "overrides, expected_status_line, expected_text",
    [
        ({}, "HTTP 200 OK", None),
        ({"status_code": 422, "reason": "Unprocessable Entity"}, "HTTP 422 Unprocessable Entity", None),
        (
            {"status_code": 302, "reason": "Found", "location": "https://login.example.com/", "body_kind": "empty"},
            "HTTP 302 Found",
            "Doorverwijzing naar: https://login.example.com/",
        ),
        ({"body": None, "body_kind": "empty"}, "HTTP 200 OK", "Het antwoord is leeg."),
        (
            {"body": None, "body_kind": "binary", "content_type": "application/pdf"},
            "HTTP 200 OK",
            "Het antwoord is een binair bestand (application/pdf) en wordt niet getoond.",
        ),
        ({"body_truncated": True}, "HTTP 200 OK", "Dit antwoord is ingekort."),
        (
            {"body_truncated": True, "timed_out": True, "duration_ms": 60000},
            "HTTP 200 OK",
            "Dit antwoord is ingekort. NotifyNL is na 60 seconden gestopt met wachten op het antwoord.",
        ),
    ],
)
def test_the_reply_of_the_endpoint_is_shown(
    logged_in_org_member,
    start_connection_test,
    connection_test_result,
    mock_events,
    overrides,
    expected_status_line,
    expected_text,
):
    connection_test_result.return_value = _finished("connected", **overrides)

    page = _test_connection(logged_in_org_member)

    result = normalize_spaces(page.select_one("#connection-test-result").text)
    assert expected_status_line in result
    if expected_text:
        assert expected_text in result


@pytest.mark.parametrize(
    "body",
    [
        '{\n  "error" :   "adres ontbreekt"\n}',
        "<script>alert(1)</script>",
    ],
)
def test_the_reply_of_the_endpoint_is_shown_as_it_was_sent_and_only_as_text(
    logged_in_org_member, start_connection_test, connection_test_result, mock_events, body
):
    connection_test_result.return_value = _finished("connected", status_code=400, reason="Bad Request", body=body)

    page = _test_connection(logged_in_org_member)

    assert page.select_one("#connection-test-result pre").text == body
    assert not page.select("#connection-test-result script")


def test_testing_the_connection_keeps_a_stored_secret_that_is_left_as_is(
    logged_in_org_member, letter_provider, start_connection_test, connection_test_result, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    _test_connection(logged_in_org_member, {"password": "secret_set"})

    assert start_connection_test.call_args.args[1]["auth_config"] == {"username": "denhaag", "password": ""}


def test_testing_the_connection_requires_the_secret_again_when_its_destination_changes(
    logged_in_org_member, letter_provider, start_connection_test, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    page = _test_connection(
        logged_in_org_member, {"endpoint_url": "https://other.example.com/letters", "password": "secret_set"}
    )

    assert _form_errors(page) == [
        "Error: Vul het wachtwoord opnieuw in: inloggegevens worden niet bewaard als een URL verandert"
    ]
    assert not start_connection_test.called
    assert not page.select_one("#connection-test-result")


def test_testing_the_connection_validates_the_form_first(logged_in_org_member, start_connection_test, mock_events):
    page = _test_connection(logged_in_org_member, {"username": ""})

    assert _form_errors(page) == ["Error: Vul de gebruikersnaam in"]
    assert not start_connection_test.called
    assert not mock_events.called


def test_testing_the_connection_waits_for_the_result(
    logged_in_org_member, start_connection_test, connection_test_result, no_waiting, mock_events
):
    connection_test_result.side_effect = [
        {"state": "queued"},
        {"state": "running", "host": "print.example.com"},
        _finished("authorized"),
    ]

    page = _test_connection(logged_in_org_member)

    assert connection_test_result.call_count == 3
    assert no_waiting.call_count == 2
    assert "Verbonden en correct geautoriseerd" in normalize_spaces(page.select_one("#connection-test-result").text)


@pytest.mark.parametrize(
    "state, expected_text",
    [
        ({"state": "queued"}, "De test staat nog in de wachtrij."),
        ({"state": "running", "host": "print.example.com"}, "NotifyNL wacht nog op antwoord van print.example.com."),
    ],
)
def test_a_connection_test_still_going_can_be_looked_up_again(
    logged_in_org_member, start_connection_test, connection_test_result, mock_events, mocker, state, expected_text
):
    mocker.patch("app.main.views_nl.organisations.letter_provider.CONNECTION_TEST_WAIT_SECONDS", 0)
    connection_test_result.return_value = state

    page = _test_connection(logged_in_org_member)

    result = normalize_spaces(page.select_one("#connection-test-result").text)
    assert expected_text in result
    assert NOT_SAVED in result
    assert not page.select(".banner-dangerous")
    assert _buttons(page) == ["Opslaan", "Verbinding testen", "Uitslag opnieuw ophalen"]
    assert page.select_one("button[name=connection_test_id]")["value"] == CONNECTION_TEST_ID
    # a signature of the tested values, not the values: the password is among them
    assert re.fullmatch("[0-9a-f]{64}", page.select_one("input[name=tested_values]")["value"])


@pytest.mark.parametrize(
    "edits, expected_note",
    [
        ({}, False),
        ({"endpoint_url": "https://other.example.com/letters"}, True),
        ({"password": "another-password"}, True),
    ],
)
def test_looking_up_a_connection_test_again_says_when_the_form_was_edited_since_it_started(
    logged_in_org_member, start_connection_test, connection_test_result, mock_events, mocker, edits, expected_note
):
    mocker.patch("app.main.views_nl.organisations.letter_provider.CONNECTION_TEST_WAIT_SECONDS", 0)
    connection_test_result.return_value = {"state": "queued"}
    tested_values = _test_connection(logged_in_org_member).select_one("input[name=tested_values]")["value"]
    connection_test_result.return_value = _finished("authorized")

    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={key: value for key, value in CONNECTION_TEST_FORM.items() if key != "test_connection"}
        | edits
        | {"connection_test_id": CONNECTION_TEST_ID, "tested_values": tested_values},
        _expected_status=200,
    )

    result = normalize_spaces(page.select_one("#connection-test-result").text)
    assert "Verbonden en correct geautoriseerd" in result
    assert (VALUES_CHANGED in result) == expected_note


def test_looking_up_a_connection_test_again_sends_no_new_letter(
    logged_in_org_member, start_connection_test, connection_test_result, mock_set_letter_provider, mock_events
):
    data = {"connection_test_id": CONNECTION_TEST_ID}
    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={key: value for key, value in CONNECTION_TEST_FORM.items() if key != "test_connection"} | data,
        _expected_status=200,
    )

    assert not start_connection_test.called
    assert not mock_set_letter_provider.called
    assert not mock_events.called
    connection_test_result.assert_called_once_with(ORGANISATION_ID, CONNECTION_TEST_ID)
    assert "Verbonden en correct geautoriseerd" in normalize_spaces(page.select_one("#connection-test-result").text)


def test_looking_up_a_connection_test_needs_a_real_id(logged_in_org_member, connection_test_result):
    logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={key: value for key, value in CONNECTION_TEST_FORM.items() if key != "test_connection"}
        | {"connection_test_id": "../../somewhere"},
        _expected_status=404,
    )

    assert not connection_test_result.called


def test_looking_up_a_connection_test_that_expired(logged_in_org_member, connection_test_result, mocker):
    response = mocker.Mock(status_code=404, json=lambda: {"result": "error", "message": "not found"})
    connection_test_result.side_effect = HTTPError(response=response, message="not found")

    page = logged_in_org_member.post(
        "main.organisation_letter_endpoint",
        org_id=ORGANISATION_ID,
        _data={key: value for key, value in CONNECTION_TEST_FORM.items() if key != "test_connection"}
        | {"connection_test_id": CONNECTION_TEST_ID},
        _expected_status=200,
    )

    assert "Deze uitslag is niet meer beschikbaar." in normalize_spaces(page.select_one("#connection-test-result").text)


def test_a_result_that_is_gone_right_after_starting_the_test(
    logged_in_org_member, start_connection_test, connection_test_result, mock_events, mocker
):
    response = mocker.Mock(status_code=404, json=lambda: {"result": "error", "message": "not found"})
    connection_test_result.side_effect = HTTPError(response=response, message="not found")

    page = _test_connection(logged_in_org_member)

    assert "Deze uitslag is niet meer beschikbaar." in normalize_spaces(page.select_one("#connection-test-result").text)


def test_testing_the_connection_where_the_api_cannot_keep_a_result(
    logged_in_org_member, start_connection_test, mock_events, mocker
):
    response = mocker.Mock(status_code=503, json=lambda: {"result": "error", "message": "needs Redis"})
    start_connection_test.side_effect = HTTPError(response=response, message="needs Redis")

    page = _test_connection(logged_in_org_member)

    assert "De verbinding kan op deze omgeving niet worden getest." in normalize_spaces(
        page.select_one("#connection-test-result").text
    )
    assert not mock_events.called


def test_testing_the_connection_too_often(logged_in_org_member, start_connection_test, mock_events, mocker):
    response = mocker.Mock(status_code=429, json=lambda: {"result": "error", "message": "Too many"})
    start_connection_test.side_effect = HTTPError(response=response, message="Too many")

    page = _test_connection(logged_in_org_member)

    assert "De verbinding is te vaak getest." in normalize_spaces(page.select_one("#connection-test-result").text)
    assert not page.select(".banner-dangerous")
    assert not mock_events.called


def test_testing_the_connection_shows_errors_from_the_api_on_the_form(
    logged_in_org_member, start_connection_test, mock_events, mocker
):
    message = f"{ENDPOINT_URL} must not point to a private or internal address"
    response = mocker.Mock(status_code=400, json=lambda: {"result": "error", "message": message})
    start_connection_test.side_effect = HTTPError(response=response, message=message)

    page = _test_connection(logged_in_org_member)

    assert normalize_spaces(page.select_one("#endpoint_url-error").text) == (
        "Error: NotifyNL kan dit adres niet gebruiken: het is onbekend of intern"
    )
    assert not page.select_one("#connection-test-result")
    assert not mock_events.called


def test_testing_the_connection_for_an_organisation_the_api_does_not_know(
    logged_in_org_member, start_connection_test, mock_events, mocker
):
    response = mocker.Mock(status_code=404, json=lambda: {"result": "error", "message": "not found"})
    start_connection_test.side_effect = HTTPError(response=response, message="not found")

    _test_connection(logged_in_org_member, _expected_status=404)
