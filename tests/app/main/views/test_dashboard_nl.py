import json

from flask import url_for

from tests import NotifyBeautifulSoup
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

    assert normalize_spaces(template_statistics.select_one("table caption").text) == "Per template"
    assert template_statistics.select(".spark-bar")

    assert [
        normalize_spaces(column.text) for column in usage.select(".govuk-grid-column-one-third .big-number-smaller")
    ] == [
        "e-mail verzonden",
        "sms verzonden",
        "brieven verzonden",
    ]


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
