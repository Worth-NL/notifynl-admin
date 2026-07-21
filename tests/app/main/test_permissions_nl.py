import pytest

from tests import sample_uuid, service_json
from tests.conftest import (
    ORGANISATION_ID,
    ORGANISATION_TWO_ID,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_folder,
    create_service_one_admin,
)

# Covers the "main.manage_users" + expected_status=200 combinations skipped in
# test_permissions.py::test_services_pages_that_org_users_are_allowed_to_see (reason:
# "[NOTIFYNL] email_domains.txt change breaks this.") - the fixture user's email is
# switched to a real domain from email_domains.txt so `is_gov_user` resolves True via
# the static check, same as it did upstream via "gov.uk".


@pytest.mark.parametrize(
    "user_services, user_organisations, organisation_checked",
    (
        ([SERVICE_ONE_ID], [], False),
        ([SERVICE_ONE_ID, SERVICE_TWO_ID], [], False),
        ([], [ORGANISATION_ID], True),
        ([SERVICE_ONE_ID], [ORGANISATION_ID], False),
        ([SERVICE_TWO_ID], [ORGANISATION_ID], True),
        ([SERVICE_ONE_ID, SERVICE_TWO_ID], [ORGANISATION_ID], False),
        ([], [ORGANISATION_ID, ORGANISATION_TWO_ID], True),
    ),
)
def test_manage_users_page_that_org_users_are_allowed_to_see(
    client_request,
    mocker,
    api_user_active,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mocked_get_service_data,
    mock_get_invites_for_service,
    mock_get_users_by_service,
    mock_get_organisation,
    mock_has_jobs,
    mock_get_service_templates,
    mock_get_service_template,
    mock_get_template_versions,
    mock_get_template_version,
    mock_get_api_keys,
    mock_template_preview,
    user_services,
    user_organisations,
    organisation_checked,
):
    api_user_active["email_address"] = "test@amsterdam.nl"
    api_user_active["services"] = user_services
    api_user_active["organisations"] = user_organisations
    api_user_active["permissions"] = {service_id: ["manage_users", "manage_settings"] for service_id in user_services}
    service = service_json(
        name="SERVICE WITH ORG",
        id_=SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        organisation_id=ORGANISATION_ID,
    )

    mocked_get_service_data[service["id"]] = service
    mocker.patch("app.template_folder_api_client.get_template_folders", return_value=[create_folder(id=sample_uuid())])

    # mock_get_users_by_service (pulled in above) hardcodes a "...gov.uk" service-user email;
    # override it here so the manage_users view's is_gov_user check resolves via the NL
    # static domain list instead of falling through to the unmocked get_domains() call.
    mocker.patch(
        "app.models.user.Users._get_items",
        side_effect=lambda service_id: [
            create_service_one_admin(
                id=sample_uuid(),
                logged_in_at=None,
                mobile_number="+447700900986",
                email_address="notify@amsterdam.nl",
            )
        ],
    )

    client_request.login(
        api_user_active,
        service=service if SERVICE_ONE_ID in user_services else None,
    )

    client_request.get("main.manage_users", service_id=SERVICE_ONE_ID, _expected_status=200, _test_page_title=False)
