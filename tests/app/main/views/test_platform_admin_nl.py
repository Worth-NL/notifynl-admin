from tests.conftest import normalize_spaces


def test_get_billing_report_when_no_results_for_date(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_billing_report",
        return_value=[],
    )

    page = client_request.post(
        "main.get_billing_report",
        _expected_status=200,
        _data={"start_date": "2019-01-01", "end_date": "2019-03-31"},
    )

    error = page.select_one(".banner-dangerous")
    assert normalize_spaces(error.text) == "Geen resultaten voor deze datums"


def test_get_dvla_billing_report_when_no_results_for_date(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_dvla_billing_report",
        return_value=[],
    )

    page = client_request.post(
        "main.get_dvla_billing_report",
        _expected_status=200,
        _data={"start_date": "2023-06-01", "end_date": "2023-06-01"},
    )

    error = page.select_one(".banner-dangerous")
    assert normalize_spaces(error.text) == "Geen resultaten voor deze datums"


def test_platform_admin_users_list_when_no_results_for_filters(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    mocker.patch(
        "app.main.views_nl.platform_admin.admin_api_client.fetch_users_list",
        return_value={"data": []},
    )

    page = client_request.post(
        "main.platform_admin_users_list",
        _expected_status=200,
        _data={"created_to_date": "2024-01-01"},
    )

    error = page.select_one(".banner-dangerous")
    assert normalize_spaces(error.text) == "Geen resultaten voor de geselecteerde filters"
