import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

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


@pytest.fixture
def org_member():
    return create_user(id=sample_uuid(), organisations=[ORGANISATION_ID])


@pytest.fixture
def letter_provider(notify_admin, mocker):
    """The organisation's letter provider as notifynl-api returns it: set .return_value to change it."""
    return mocker.patch("app.organisations_client.get_organisation_letter_provider", return_value=PINGEN)


@pytest.fixture
def mock_set_letter_provider(notify_admin, mocker):
    def _set(org_id, data, cached_service_ids=None):
        return {"pingen": PINGEN}.get(data["provider"], REST_ENDPOINT | {"endpoint_url": data.get("endpoint_url")})

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
        "main.organisation_letter_provider",
        "main.organisation_change_letter_provider",
        "main.organisation_letter_endpoint",
    ],
)
def test_any_organisation_member_can_manage_the_letter_provider(logged_in_org_member, endpoint):
    logged_in_org_member.get(endpoint, org_id=ORGANISATION_ID)


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.organisation_letter_provider",
        "main.organisation_change_letter_provider",
        "main.organisation_letter_endpoint",
    ],
)
def test_platform_admins_can_manage_the_letter_provider(
    client_request, platform_admin_user, mock_get_organisation, letter_provider, endpoint
):
    client_request.login(platform_admin_user)
    client_request.get(endpoint, org_id=ORGANISATION_ID)


@pytest.mark.parametrize(
    "endpoint, method",
    [
        ("main.organisation_letter_provider", "get"),
        ("main.organisation_change_letter_provider", "post"),
        ("main.organisation_letter_endpoint", "post"),
    ],
)
def test_other_users_cannot_manage_the_letter_provider(
    client_request, mock_get_organisation, letter_provider, mock_set_letter_provider, endpoint, method
):
    client_request.login(create_user(id=sample_uuid(), organisations=[sample_uuid()]))

    getattr(client_request, method)(endpoint, org_id=ORGANISATION_ID, _expected_status=403)

    assert not mock_set_letter_provider.called


@pytest.mark.parametrize(
    "endpoint",
    ["main.organisation_settings", "main.edit_organisation_area_boundary"],
)
def test_organisation_settings_stay_platform_admin_only(logged_in_org_member, endpoint):
    logged_in_org_member.get(endpoint, org_id=ORGANISATION_ID, _expected_status=403)


def test_organisation_nav_shows_brieven_to_organisation_members(logged_in_org_member, mocker):
    mocker.patch("app.organisations_client.get_services_and_usage", return_value={"services": [], "updated_at": None})

    page = logged_in_org_member.get("main.organisation_letter_provider", org_id=ORGANISATION_ID)

    nav_items = [normalize_spaces(item.text) for item in page.select("nav.navigation a")]
    assert nav_items == ["Gebruik", "Teamleden", "Brieven"]
    assert "selected" in page.select_one("nav.navigation a[href$='/letter-provider']")["class"]


@pytest.mark.parametrize("pingen", [PINGEN, None])
def test_letter_provider_page_for_pingen(logged_in_org_member, letter_provider, pingen):
    letter_provider.return_value = pingen

    page = logged_in_org_member.get("main.organisation_letter_provider", org_id=ORGANISATION_ID)

    rows = [normalize_spaces(row.text) for row in page.select(".govuk-summary-list__row")]
    assert rows == [
        "Printleverancier Pingen Wijzigen printleverancier",
        "Adres op de brief 60 mm vanaf de bovenkant (vast bij Pingen)",
    ]
    assert not page.select(".govuk-warning-text")


def test_letter_provider_page_for_a_rest_endpoint(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT

    page = logged_in_org_member.get("main.organisation_letter_provider", org_id=ORGANISATION_ID)

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


def test_letter_provider_page_warns_about_an_incomplete_rest_endpoint(logged_in_org_member, letter_provider):
    letter_provider.return_value = REST_ENDPOINT | {"has_credentials": False, "is_complete": False}

    page = logged_in_org_member.get("main.organisation_letter_provider", org_id=ORGANISATION_ID)

    assert "stuurt NotifyNL uw brieven naar Pingen" in normalize_spaces(page.select_one(".govuk-warning-text").text)


def test_change_letter_provider_page_warns_about_letters_in_progress(logged_in_org_member):
    page = logged_in_org_member.get("main.organisation_change_letter_provider", org_id=ORGANISATION_ID)

    assert page.select_one("input[name=provider][checked]")["value"] == "pingen"
    assert "gaan naar de nieuwe printleverancier" in normalize_spaces(page.select_one(".govuk-warning-text").text)


def test_choosing_a_rest_endpoint_goes_to_its_settings(logged_in_org_member, mock_set_letter_provider):
    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "rest-endpoint"},
        _expected_redirect=url_for("main.organisation_letter_endpoint", org_id=ORGANISATION_ID),
    )

    assert not mock_set_letter_provider.called


def test_choosing_pingen_saves_it_and_logs_an_event(
    logged_in_org_member, org_member, letter_provider, mock_set_letter_provider, organisation_services, mock_events
):
    letter_provider.return_value = REST_ENDPOINT

    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "pingen"},
        _expected_redirect=url_for("main.organisation_letter_provider", org_id=ORGANISATION_ID),
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
    }


def test_choosing_pingen_again_changes_nothing(logged_in_org_member, mock_set_letter_provider, mock_events):
    logged_in_org_member.post(
        "main.organisation_change_letter_provider",
        org_id=ORGANISATION_ID,
        _data={"provider": "pingen"},
        _expected_redirect=url_for("main.organisation_letter_provider", org_id=ORGANISATION_ID),
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
        _expected_redirect=url_for("main.organisation_letter_provider", org_id=ORGANISATION_ID),
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
    # never any credentials in the audit event
    assert not {"auth_config", "password", "api_key", "client_secret"} & set(event_data)
    assert not {"hunter2", "k3y", "s3cret"} & {str(value) for value in event_data.values()}


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
