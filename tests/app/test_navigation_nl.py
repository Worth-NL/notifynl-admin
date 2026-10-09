from unittest.mock import Mock

from flask import url_for
from notifications_python_client.errors import HTTPError

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_navigation_displayed_on_service_page_404(
    client_request,
    mock_get_job_doesnt_exist,
    fake_uuid,
):
    page = client_request.get(
        "main.view_job",
        service_id="596364a0-858e-42c8-9062-a8fe822260eb",
        job_id=fake_uuid,
        _expected_status=404,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Pagina niet gevonden"
    assert normalize_spaces(page.select_one(".navigation-service-name").text) == "service one"
    assert len(page.select("nav.navigation .navigation__item")) == 8


def test_navigation_and_custom_error_displayed_on_notification_page_404_nl(client_request, mocker, fake_uuid):
    mock_get_notification = mocker.patch(
        "app.notification_api_client.get_notification",
        side_effect=HTTPError(response=Mock(status_code=404)),
    )

    page = client_request.get(
        "main.view_notification",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        _expected_status=404,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Pagina niet gevonden"
    assert normalize_spaces(page.select_one(".navigation-service-name").text) == "service one"
    assert len(page.select("nav.navigation .navigation__item")) == 8
    assert page.select_one('a:-soup-contains("Bewaartermijn van gegevens")')["href"] == url_for(
        "main.guidance_data_retention_period"
    )
    mock_get_notification.assert_called_once()
