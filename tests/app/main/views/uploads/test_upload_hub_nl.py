import pytest
from freezegun import freeze_time

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


@pytest.mark.parametrize(
    "now, expected_statement",
    [
        ("2017-10-10 10:10:10", "Verstuurd vandaag"),
        # notifynl-api groups letters uploaded after 17:30 under the next day
        ("2017-10-09 19:00:00", "Verstuurd vandaag"),
        ("2017-10-11 10:10:10", "Verstuurd gisteren"),
        ("2017-10-13 10:10:10", "Verstuurd op 10 oktober"),
    ],
)
def test_upload_hub_says_when_a_day_of_uploaded_letters_was_sent(
    client_request, service_one, mock_get_uploads, mock_get_no_contact_lists, mocker, now, expected_statement
):
    mocker.patch("app.job_api_client.get_jobs", return_value={"data": []})
    service_one["permissions"] += ["letter"]

    with freeze_time(now):
        page = client_request.get("main.uploads", service_id=SERVICE_ONE_ID)

    letter_day = page.select(".govuk-summary-list__row")[0]
    assert normalize_spaces(letter_day.select_one(".notify-summary-list__metadata").text) == expected_statement


@pytest.mark.parametrize("now", ["2020-02-02 14:00", "2020-02-02 18:00", "2020-02-05 09:00"])
def test_uploaded_letters_page_says_how_letters_are_sent(client_request, mock_get_uploaded_letters, now):
    with freeze_time(now):
        page = client_request.get("main.uploaded_letters", service_id=SERVICE_ONE_ID, letter_print_day="2020-02-02")

    assert normalize_spaces(page.select("main p")[1].text) == (
        "NotifyNL stuurt brieven binnen enkele minuten naar de printleverancier."
    )
