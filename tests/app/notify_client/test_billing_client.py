import uuid

import pytest

from app.notify_client.billing_api_client import BillingAPIClient


def test_get_free_sms_fragment_limit_for_year_correct_endpoint(mocker):
    service_id = uuid.uuid4()
    expected_url = f"/service/{service_id}/billing/free-sms-fragment-limit"
    client = BillingAPIClient(mocker.MagicMock())

    mock_get = mocker.patch("app.notify_client.billing_api_client.BillingAPIClient.get")

    client.get_free_sms_fragment_limit_for_year(service_id, year=1999)
    mock_get.assert_called_once_with(expected_url, params={"financial_year_start": 1999})


def test_post_create_or_update_free_sms_fragment_limit(mocker):
    service_id = uuid.uuid4()
    mock_post = mocker.patch("app.notify_client.billing_api_client.BillingAPIClient.post")
    client = BillingAPIClient(mocker.MagicMock())

    client.create_or_update_free_sms_fragment_limit(service_id=service_id, free_sms_fragment_limit=1111)

    mock_post.assert_called_once_with(
        url=f"/service/{service_id}/billing/free-sms-fragment-limit",
        data={"free_sms_fragment_limit": 1111},
    )


@pytest.mark.parametrize(
    "func, expected_url",
    [
        (BillingAPIClient.get_data_for_volumes_by_service_report, "/platform-stats/volumes-by-service"),
        (BillingAPIClient.get_data_for_daily_volumes_report, "/platform-stats/daily-volumes-report"),
        (
            BillingAPIClient.get_data_for_daily_sms_provider_volumes_report,
            "/platform-stats/daily-sms-provider-volumes-report",
        ),
    ],
)
def test_get_data_for_volume_reports(mocker, func, expected_url):
    mock_get = mocker.patch("app.notify_client.billing_api_client.BillingAPIClient.get")
    client = BillingAPIClient(mocker.MagicMock())

    func(client, "2022-03-01", "2022-03-31")

    mock_get.assert_called_once_with(url=expected_url, params={"start_date": "2022-03-01", "end_date": "2022-03-31"})
