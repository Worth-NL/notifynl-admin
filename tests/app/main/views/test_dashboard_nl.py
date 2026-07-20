from flask import url_for

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
