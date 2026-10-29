from unittest.mock import call

import pytest
from freezegun import freeze_time

from app import billing_api_client
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize(
    "method, api_response, expected_value, expected_key",
    (
        ("get_monthly_usage_for_service", [{"month": "April"}], [{"month": "April"}], "monthly-usage"),
        (
            "get_annual_usage_for_service",
            [{"notification_type": "sms"}],
            [{"notification_type": "sms"}],
            "annual-usage",
        ),
        (
            "get_free_sms_fragment_limit_for_year",
            {"free_sms_fragment_limit": 250000},
            250000,
            "free-sms-fragment-limit",
        ),
    ),
)
@pytest.mark.parametrize(
    "year, expected_ttl",
    (
        (2012, 900),  # current year: refreshed hourly by the API
        (None, 900),  # the API's default is the current year
        (2011, 86_400),
    ),
)
@freeze_time("2012-06-01 12:00")
def test_usage_is_cached_for_less_time_in_the_current_year(
    notify_admin, mocker, method, api_response, expected_value, expected_key, year, expected_ttl
):
    mock_redis_get = mocker.patch("app.extensions.RedisClient.get", return_value=None)
    mock_redis_set = mocker.patch("app.extensions.RedisClient.set")
    mocker.patch("app.notify_client.NotifyAdminAPIClient.get", return_value=api_response)

    assert getattr(billing_api_client, method)(SERVICE_ONE_ID, year) == expected_value

    redis_key = f"service-{SERVICE_ONE_ID}-billing-{expected_key}-{year}"
    assert mock_redis_get.call_args_list == [call(redis_key, skippable=True)]
    mock_redis_set.assert_called_once()
    assert mock_redis_set.call_args.args[0] == redis_key
    assert mock_redis_set.call_args.kwargs["ex"] == expected_ttl


def test_cached_usage_does_not_call_the_api(notify_admin, mocker):
    mocker.patch("app.extensions.RedisClient.get", return_value=b'[{"month": "April"}]')
    mock_api_get = mocker.patch("app.notify_client.NotifyAdminAPIClient.get")

    assert billing_api_client.get_monthly_usage_for_service(SERVICE_ONE_ID, 2012) == [{"month": "April"}]
    assert not mock_api_get.called


def test_updating_the_free_sms_allowance_clears_its_cache(notify_admin, mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_delete_by_pattern = mocker.patch("app.extensions.RedisClient.delete_by_pattern")
    mocker.patch("app.notify_client.NotifyAdminAPIClient.post")

    billing_api_client.create_or_update_free_sms_fragment_limit(SERVICE_ONE_ID, 1000)

    pattern = f"service-{SERVICE_ONE_ID}-billing-free-sms-fragment-limit-*"
    assert mock_delete_by_pattern.call_args_list == [call(pattern, raise_exception=True)] * 2


def test_get_usage_updated_at(notify_admin, mocker):
    mock_api_get = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.get", return_value={"updated_at": "2012-06-01T11:00:00+00:00"}
    )

    assert billing_api_client.get_usage_updated_at(SERVICE_ONE_ID) == "2012-06-01T11:00:00+00:00"
    mock_api_get.assert_called_once_with(f"/service/{SERVICE_ONE_ID}/billing/usage-updated-at")


def test_get_free_sms_fragment_limit_for_year_correct_endpoint(notify_admin, mocker):
    mock_get = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.get", return_value={"free_sms_fragment_limit": 250000}
    )

    assert billing_api_client.get_free_sms_fragment_limit_for_year(SERVICE_ONE_ID, year=1999) == 250000
    mock_get.assert_called_once_with(
        f"/service/{SERVICE_ONE_ID}/billing/free-sms-fragment-limit", params={"financial_year_start": 1999}
    )
