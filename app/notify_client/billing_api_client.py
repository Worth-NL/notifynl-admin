from contextvars import ContextVar
from datetime import timedelta

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache
from app.utils.time import get_current_financial_year

# [NOTIFYNL] the API refreshes the current year's usage hourly; earlier years only change around the year boundary
CURRENT_YEAR_TTL_IN_SECONDS = int(timedelta(minutes=15).total_seconds())
PAST_YEAR_TTL_IN_SECONDS = int(timedelta(days=1).total_seconds())


def _cached_for_year(value, year):
    """[NOTIFYNL] `year=None` means the current financial year to the API."""
    is_past_year = year is not None and int(year) < get_current_financial_year()
    return cache.CacheResultWrapper(
        value=value,
        cache_decision=True,
        ttl_in_seconds_override=PAST_YEAR_TTL_IN_SECONDS if is_past_year else CURRENT_YEAR_TTL_IN_SECONDS,
    )


class BillingAPIClient(NotifyAdminAPIClient):
    @cache.set("service-{service_id}-billing-monthly-usage-{year}")  # [NOTIFYNL]
    def get_monthly_usage_for_service(self, service_id, year):
        return _cached_for_year(self.get(f"/service/{service_id}/billing/monthly-usage", params={"year": year}), year)

    @cache.set("service-{service_id}-billing-annual-usage-{year}")  # [NOTIFYNL]
    def get_annual_usage_for_service(self, service_id, year=None):
        return _cached_for_year(
            self.get(f"/service/{service_id}/billing/yearly-usage-summary", params={"year": year}), year
        )

    @cache.set("service-{service_id}-billing-free-sms-fragment-limit-{year}")  # [NOTIFYNL]
    def get_free_sms_fragment_limit_for_year(self, service_id, year=None):
        result = self.get(
            f"/service/{service_id}/billing/free-sms-fragment-limit", params={"financial_year_start": year}
        )
        return _cached_for_year(result["free_sms_fragment_limit"], year)

    def get_usage_updated_at(self, service_id):
        """[NOTIFYNL] When the API last refreshed today's usage, or None before its first hourly run."""
        return self.get(f"/service/{service_id}/billing/usage-updated-at")["updated_at"]

    @cache.delete_by_pattern("service-{service_id}-billing-free-sms-fragment-limit-*")  # [NOTIFYNL]
    def create_or_update_free_sms_fragment_limit(self, service_id, free_sms_fragment_limit):
        """
        Updates the free sms fragment limit for the current financial year
        """
        data = {"free_sms_fragment_limit": free_sms_fragment_limit}

        return self.post(url=f"/service/{service_id}/billing/free-sms-fragment-limit", data=data)

    def get_data_for_billing_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/data-for-billing-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_dvla_billing_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/data-for-dvla-billing-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_volumes_by_service_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/volumes-by-service",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_daily_volumes_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/daily-volumes-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_data_for_daily_sms_provider_volumes_report(self, start_date, end_date):
        return self.get(
            url="/platform-stats/daily-sms-provider-volumes-report",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )


_billing_api_client_context_var: ContextVar[BillingAPIClient | None] = ContextVar("billing_api_client")
get_billing_api_client: LazyLocalGetter[BillingAPIClient] = LazyLocalGetter(
    _billing_api_client_context_var,
    lambda: BillingAPIClient(current_app),
)
memo_resetters.append(lambda: get_billing_api_client.clear())
billing_api_client: BillingAPIClient = LocalProxy(get_billing_api_client)  # type: ignore[assignment]
