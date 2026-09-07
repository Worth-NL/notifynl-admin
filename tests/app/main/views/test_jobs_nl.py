import uuid

import pytest
from freezegun import freeze_time

from tests import job_json, notification_json
from tests.conftest import SERVICE_ONE_ID


@freeze_time("2019-06-20 17:30:00.000001")
@pytest.mark.parametrize(
    "job_created_at, expected_fragment",
    [
        ("2019-06-20T15:30:00.000001+00:00", "vandaag"),
        ("2019-06-19T15:30:00.000001+00:00", "gisteren"),
        ("2019-06-18T15:30:00.000001+00:00", "op 18 juni"),
    ],
)
def test_should_not_show_cancel_link_for_letter_job_if_too_late(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_get_service_data_retention,
    active_user_with_permissions,
    job_created_at,
    expected_fragment,
):
    job_id = uuid.uuid4()
    job = job_json(SERVICE_ONE_ID, active_user_with_permissions, job_id=job_id, created_at=job_created_at)
    notifications_json = notification_json(SERVICE_ONE_ID, job=job, status="created", template_type="letter")
    mocker.patch("app.job_api_client.get_job", side_effect=[{"data": job}])
    mocker.patch("app.models.notification.Notifications._get_items", return_value=notifications_json)

    page = client_request.get("main.view_job", service_id=SERVICE_ONE_ID, job_id=str(job_id))

    assert "Cancel sending these letters" not in page
    assert page.select_one("p#printing-info").text.strip() == f"Geprint {expected_fragment} om 17:30 uur"
