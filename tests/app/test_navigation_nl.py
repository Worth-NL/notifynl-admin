from tests.conftest import normalize_spaces


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
