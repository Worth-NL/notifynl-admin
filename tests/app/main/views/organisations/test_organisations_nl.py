import pytest
from freezegun import freeze_time

from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces


@pytest.mark.parametrize(
    "service_usage, expected_css_class",
    (
        (
            {"emails_sent": 999_999_999, "sms_cost": 0, "letter_cost": 0, "letters_sent": 0},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 1_000_000_000, "sms_cost": 0, "letter_cost": 0, "letters_sent": 0},
            ".big-number-smallest",
        ),
        (
            {"emails_sent": 0, "sms_cost": 999_999, "letter_cost": 0, "letters_sent": 0},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 0, "sms_cost": 1_000_000, "letter_cost": 0, "letters_sent": 0},
            ".big-number-smallest",
        ),
        (
            {"emails_sent": 0, "sms_cost": 0, "letter_cost": 999_999, "letters_sent": 0},
            ".big-number-smaller",
        ),
        (
            {"emails_sent": 0, "sms_cost": 0, "letter_cost": 1_000_000, "letters_sent": 0},
            ".big-number-smallest",
        ),
    ),
)
@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_usage_in_correct_font_size(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    service_usage,
    expected_css_class,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                service_usage
                | {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "1",
                    "chargeable_billable_sms": 1,
                    "free_sms_limit": 250000,
                    "sms_billable_units": 1,
                    "sms_remainder": None,
                    "letters_sent": 0,
                },
            ],
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    usage_totals = page.select_one("main .govuk-grid-row").select(expected_css_class)

    assert len(usage_totals) == 3


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_search_bar(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 1.93,
                    "sms_remainder": None,
                    "letters_sent": 0,
                },
            ]
            * 8,
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 8

    assert page.select_one(".live-search")["data-targets"] == ".organisation-service"
    assert [normalize_spaces(service_name.text) for service_name in page.select(".live-search-relevant")] == [
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
    ]


@freeze_time("2020-02-20 20:20")
def test_organisation_services_hides_search_bar_for_7_or_fewer_services(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
):
    mocker.patch(
        "app.organisations_client.get_services_and_usage",
        return_value={
            "services": [
                {
                    "service_id": SERVICE_ONE_ID,
                    "service_name": "Service 1",
                    "chargeable_billable_sms": 250122,
                    "emails_sent": 13000,
                    "free_sms_limit": 250000,
                    "letter_cost": 30.50,
                    "sms_billable_units": 122,
                    "sms_cost": 1.93,
                    "sms_remainder": None,
                    "letters_sent": 800,
                },
            ]
            * 7,
            "updated_at": None,
        },
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 7
    assert not page.select_one(".live-search")
