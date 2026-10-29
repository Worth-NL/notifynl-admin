import json

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import NotifyBeautifulSoup, service_json
from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_service_dashboard_skeleton(
    client_request,
    mock_get_service_templates,
    mock_has_no_jobs,
    mock_get_unsubscribe_requests_statistics,
    mock_get_inbound_sms_summary,
    mock_get_returned_letter_statistics_with_no_returned_letters,
):
    page = client_request.get("main.service_dashboard", service_id=SERVICE_ONE_ID)

    assert [(heading.name, normalize_spaces(heading.text)) for heading in page.select("main h1, main h2, main h3")] == [
        ("h1", "Dashboard"),
        ("h2", "Afgelopen 7 dagen"),
        ("h2", "Per template"),
        ("h2", "Dit jaar"),
    ]

    totals = page.select_one("[data-key=totals]")
    template_statistics = page.select_one("[data-key=template-statistics]")
    usage = page.select_one("[data-key=usage]")

    assert totals["data-resource"] == url_for(
        "json_updates.service_dashboard_updates",
        service_id=SERVICE_ONE_ID,
    )
    assert template_statistics["data-resource"] == url_for(
        "json_updates.service_dashboard_updates",
        service_id=SERVICE_ONE_ID,
    )
    assert usage["data-resource"] == url_for(
        "json_updates.service_dashboard_usage_updates",
        service_id=SERVICE_ONE_ID,
    )

    assert [normalize_spaces(column.text) for column in totals.select(".big-number-with-status")] == [
        "e-mails verstuurd mislukt – Onbekend %",
        "SMS-berichten verstuurd mislukt – Onbekend %",
        "brieven verstuurd mislukt – Onbekend %",
    ]

    assert normalize_spaces(template_statistics.select_one("h2").text) == "Per template"
    assert template_statistics.select(".spark-bar")

    assert [
        normalize_spaces(column.text) for column in usage.select(".govuk-grid-column-one-third .big-number-smaller")
    ] == [
        "e-mail verzonden",
        "sms verzonden",
        "brieven verzonden",
        "berichtenbox verzonden",
    ]


def test_service_dashboard_skeleton_shows_messagebox_placeholder_for_messagebox_service(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_has_no_jobs,
    mock_get_unsubscribe_requests_statistics,
    mock_get_inbound_sms_summary,
    mock_get_returned_letter_statistics_with_no_returned_letters,
):
    # Regression test: app/templates_nl/views/dashboard/_totals-lazy.html once only reserved
    # 3 loading tiles (email/sms/letter), unlike its sibling _usage-lazy.html which already
    # reserves a 4th spot for messagebox - so for a service with the messagebox permission, the
    # Berichtenbox totals tile used to pop in only once the AJAX call resolved, shifting the rest
    # of the page down.
    service_one["permissions"] = ["email", "sms", "letter", "messagebox"]

    page = client_request.get("main.service_dashboard", service_id=SERVICE_ONE_ID)

    totals = page.select_one("[data-key=totals]")

    assert [normalize_spaces(column.text) for column in totals.select(".big-number-with-status")] == [
        "e-mails verstuurd mislukt – Onbekend %",
        "SMS-berichten verstuurd mislukt – Onbekend %",
        "brieven verstuurd mislukt – Onbekend %",
        "berichten verstuurd mislukt – Onbekend %",
    ]


@freeze_time("2016-07-01 12:00")  # 4 months into 2016 financial year
def test_template_usage_hides_link_for_precompiled_letter_template(
    client_request,
    mocker,
    fake_uuid,
):
    # Regression test: app/templates_nl/views/dashboard/all-template-statistics.html once
    # linked every stat row to main.view_template unconditionally, including the service's
    # hidden "Pre-compiled PDF" system template - which 404s, since every single-template
    # fetch filters hidden=False. template-statistics.html's sibling widget already guards
    # this with is_precompiled_letter; this page needed the same guard.
    precompiled_template_id = "6ce466d0-fd6a-11e5-82f5-e0accb9d11a7"
    mocker.patch(
        "app.template_statistics_client.get_monthly_template_usage_for_service",
        return_value=[
            {
                "template_id": fake_uuid,
                "month": 4,
                "year": 2016,
                "count": 2,
                "name": "Mijn eerste sjabloon",
                "type": "sms",
                "is_precompiled_letter": False,
            },
            {
                "template_id": precompiled_template_id,
                "month": 4,
                "year": 2016,
                "count": 1,
                "name": "Pre-compiled PDF",
                "type": "letter",
                "is_precompiled_letter": True,
            },
        ],
    )

    page = client_request.get("main.template_usage", service_id=SERVICE_ONE_ID)

    table_rows = page.select(".govuk-summary-list__row")
    assert len(table_rows) == 2

    normal_row, precompiled_row = table_rows
    assert normal_row.select_one("a")["href"] == url_for(
        "main.view_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid
    )
    assert normalize_spaces(normal_row.text) == "Mijn eerste sjabloon Sms-bericht sjabloon 2"

    assert precompiled_row.select_one("a") is None
    assert normalize_spaces(precompiled_row.text) == "Aangeleverd als pdf Brief 1"


def test_service_dashboard_updates_shows_correct_totals_labels(
    client_request,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_unsubscribe_requests_statistics,
    mock_has_no_jobs,
    mock_get_annual_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_inbound_sms_summary,
    mock_get_returned_letter_statistics_with_no_returned_letters,
    mocker,
):
    # Regression test: app/templates_nl/views/dashboard/_totals.html once passed the Dutch noun
    # ("e-mail"/"brief") as the message_type argument to message_count_label instead of the
    # literal message_type key ("email"/"letter") that message_count_noun actually switches on,
    # so it silently fell back to the generic "bericht(en)" label instead of "e-mail(s)"/"brief(ven)".
    mocker.patch(
        "app.main.views_nl.dashboard.get_dashboard_totals",
        return_value={
            "email": {"requested": 123, "delivered": 0, "failed": 0},
            "sms": {"requested": 456, "delivered": 0, "failed": 0},
            "letter": {"requested": 789, "delivered": 0, "failed": 0},
        },
    )

    json_response = client_request.get_response("json_updates.service_dashboard_updates", service_id=SERVICE_ONE_ID)
    json_content = json.loads(json_response.get_data(as_text=True))
    totals_partial = NotifyBeautifulSoup(json_content["totals"], "html.parser")

    labels = [normalize_spaces(label.text) for label in totals_partial.select(".big-number-label")]
    assert labels == [
        "e-mails verstuurd",
        "SMS-berichten verstuurd",
        "brieven verstuurd",
    ]


@pytest.mark.parametrize("service_restricted, expected_tag", [(True, "Proefmodus"), (False, None)])
def test_service_navigation_shows_if_service_is_in_trial_mode(
    mock_get_service_templates_when_no_templates_exist,
    mock_has_no_jobs,
    mock_get_unsubscribe_requests_statistics,
    mock_get_returned_letter_statistics_with_no_returned_letters,
    api_user_active,
    client_request,
    service_restricted,
    expected_tag,
    mocker,
):
    service = service_json(SERVICE_ONE_ID, users=[api_user_active["id"]], restricted=service_restricted)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})

    page = client_request.get("main.service_dashboard", service_id=SERVICE_ONE_ID)

    tag = page.select_one(".navigation-status-tag")
    assert (normalize_spaces(tag.text) if tag else None) == expected_tag


def _get_usage_partials(client_request, **kwargs):
    json_response = client_request.get_response("json_updates.usage_updates", service_id=SERVICE_ONE_ID, **kwargs)
    json_content = json.loads(json_response.get_data(as_text=True))
    assert json_content["stop"] == 1
    return (
        NotifyBeautifulSoup(json_content["usage"], "html.parser"),
        NotifyBeautifulSoup(json_content["updated_at"], "html.parser"),
    )


@freeze_time("2012-03-31 12:12:12")
def test_usage_page_shows_the_years_and_loads_the_usage_later(
    client_request,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
):
    page = client_request.get("main.usage", service_id=SERVICE_ONE_ID)

    assert not mock_get_monthly_usage_for_service.called
    assert not mock_get_annual_usage_for_service.called
    assert not mock_get_free_sms_fragment_limit.called

    nav = page.select_one("ul.pill")
    assert normalize_spaces(nav.find("a", {"aria-current": "page"}).text) == "2011 to 2012 financial year"
    assert [normalize_spaces(link.text) for link in nav.select("a:not(.pill-item--selected)")] == [
        "2010 to 2011 financial year",
        "2009 to 2010 financial year",
    ]

    blocks = page.select("[data-notify-module=update-content]")
    assert [block["data-key"] for block in blocks] == ["updated_at", "usage"]
    assert {block["data-resource"] for block in blocks} == {
        url_for("json_updates.usage_updates", service_id=SERVICE_ONE_ID, year=2011)
    }

    usage = page.select_one("[data-key=usage]")
    assert [normalize_spaces(heading.text) for heading in usage.select("h2")] == [
        "E-mails",
        "Sms-berichten",
        "Brieven",
        "Berichtenbox",
    ]
    assert len(usage.select(".loading-indicator")) == 4
    assert not usage.select("table")


def test_usage_page_passes_the_year_to_usage_json(client_request):
    page = client_request.get("main.usage", service_id=SERVICE_ONE_ID, year=2000)

    assert page.select_one("[data-key=usage]")["data-resource"] == url_for(
        "json_updates.usage_updates", service_id=SERVICE_ONE_ID, year=2000
    )


@pytest.mark.parametrize("endpoint", ["main.usage", "json_updates.usage_updates"])
def test_usage_for_invalid_year(client_request, endpoint):
    client_request.get_response(endpoint, service_id=SERVICE_ONE_ID, year="abcd", _expected_status=404)


@freeze_time("2012-03-31 12:12:12")
def test_usage_json(
    client_request,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocker,
):
    mocker.patch("app.billing_api_client.get_usage_updated_at", return_value="2012-03-31T11:12:12+00:00")

    usage, _ = _get_usage_partials(client_request)

    mock_get_monthly_usage_for_service.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_annual_usage_for_service.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_free_sms_fragment_limit.assert_called_once_with(SERVICE_ONE_ID, 2011)

    columns = [normalize_spaces(column.text) for column in usage.select(".govuk-grid-column-one-third")]
    assert columns == [
        # format_thousands keeps the comma: existing behaviour of the NL formatters, not this page
        "E-mails 1,000 verzonden",
        "Sms-berichten 251,800 verzonden",
        "Brieven 100 verzonden",
        "Berichtenbox 0 verzonden",
    ]


@pytest.mark.parametrize(
    "now, expected_number_of_months",
    [(freeze_time("2017-03-31 11:09:00.061258"), 12), (freeze_time("2017-01-01 11:09:00.061258"), 10)],
)
def test_usage_json_monthly_breakdown_shows_months_so_far(
    client_request,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocker,
    now,
    expected_number_of_months,
):
    mocker.patch("app.billing_api_client.get_usage_updated_at", return_value=None)

    with now:
        usage, _ = _get_usage_partials(client_request)

    assert len(usage.select_one("table").select("tr.table-row")) == expected_number_of_months


@freeze_time("2012-03-31 12:12:12")
def test_usage_json_monthly_breakdown(
    client_request,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocker,
):
    mocker.patch("app.billing_api_client.get_usage_updated_at", return_value=None)

    usage, _ = _get_usage_partials(client_request)

    row_for_feb = usage.select_one("table").select("tr.table-row")[10]
    assert [normalize_spaces(item.text) for item in row_for_feb.select(r"li.govuk-\!-font-tabular-numbers")] == [
        "1,234 SMS-berichten",
        "1,234 SMS-berichten",
        "10 Nederland brieven",
        "3 Europa brieven",
        "6 Rest van de wereld brieven",
        "5 Rest van de wereld brieven",
        "7 Rest van de wereld brieven",
    ]


@pytest.mark.parametrize(
    "annual_usage, expected_css_class",
    (
        (
            [{"notification_type": "sms", "chargeable_units": 1, "charged_units": 1, "rate": 1, "cost": 99_999}],
            ".big-number-smaller",
        ),
        (
            [{"notification_type": "sms", "chargeable_units": 1, "charged_units": 1, "rate": 1, "cost": 100_000}],
            ".big-number-smallest",
        ),
        ([{"notification_type": "email", "notifications_sent": 999_999_999}], ".big-number-smaller"),
        ([{"notification_type": "email", "notifications_sent": 1_000_000_000}], ".big-number-smallest"),
        ([{"notification_type": "letter", "notifications_sent": 1, "cost": 99_999}], ".big-number-smaller"),
        ([{"notification_type": "letter", "notifications_sent": 1, "cost": 100_000}], ".big-number-smallest"),
    ),
)
@freeze_time("2012-03-31 12:12:12")
def test_usage_json_font_size(
    client_request,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocker,
    annual_usage,
    expected_css_class,
):
    mocker.patch("app.billing_api_client.get_annual_usage_for_service", return_value=annual_usage)
    mocker.patch("app.billing_api_client.get_usage_updated_at", return_value=None)

    usage, _ = _get_usage_partials(client_request)

    assert len(usage.select(f".govuk-grid-row {expected_css_class}")) == 4


@freeze_time("2012-03-31 12:12:12")
def test_usage_json_for_a_future_year(
    client_request,
    mock_get_annual_usage_for_service_in_future,
    mock_get_monthly_usage_for_service_in_future,
    mock_get_free_sms_fragment_limit,
    mocker,
):
    mock_get_updated_at = mocker.patch("app.billing_api_client.get_usage_updated_at")

    usage, updated_at = _get_usage_partials(client_request, year=2014)

    mock_get_monthly_usage_for_service_in_future.assert_called_once_with(SERVICE_ONE_ID, 2014)
    mock_get_annual_usage_for_service_in_future.assert_called_once_with(SERVICE_ONE_ID, 2014)
    mock_get_free_sms_fragment_limit.assert_called_once_with(SERVICE_ONE_ID, 2014)
    assert not mock_get_updated_at.called
    assert normalize_spaces(updated_at.text) == ""
    assert not usage.select("tr.table-row li.govuk-\\!-font-tabular-numbers")


@pytest.mark.parametrize(
    "year, updated_at, expected_text",
    (
        (None, "2012-03-31T11:12:12+00:00", "Laatst bijgewerkt vandaag om 12:12"),
        (None, None, ""),
        (2010, "2012-03-31T11:12:12+00:00", ""),
    ),
)
@freeze_time("2012-03-31 12:12:12")
def test_usage_json_shows_when_the_current_year_was_last_updated(
    client_request,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocker,
    year,
    updated_at,
    expected_text,
):
    mocker.patch("app.billing_api_client.get_usage_updated_at", return_value=updated_at)

    _, updated_at_partial = _get_usage_partials(client_request, **({"year": year} if year else {}))

    assert normalize_spaces(updated_at_partial.select_one("p.heading-aside").text) == expected_text
