import pytest
from freezegun import freeze_time

from tests.conftest import (
    SERVICE_ONE_ID,
    create_notification,
    do_mock_get_page_counts_for_letter,
    normalize_spaces,
)


def test_show_cancel_letter_confirmation(client_request, mocker, fake_uuid, mock_get_page_counts_for_letter):
    notification = create_notification(template_type="letter", notification_status="created")
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)

    page = client_request.get(
        "main.cancel_letter",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    flash_message = normalize_spaces(page.select_one("div.banner-dangerous").text)

    assert "Weet u zeker dat u het versturen van deze brief wilt annuleren?" in flash_message


def test_notification_page_shows_validation_failed_precompiled_letter(
    client_request,
    mocker,
    fake_uuid,
):
    notification = create_notification(
        template_type="letter", notification_status="validation-failed", is_precompiled_letter=True
    )
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)
    metadata = {
        "page_count": "1",
        "status": "validation-failed",
        "invalid_pages": "[1]",
        "message": "content-outside-printable-area",
    }
    mocker.patch("app.main.views_nl.notifications.get_letter_file_data", return_value=("some letter content", metadata))
    do_mock_get_page_counts_for_letter(mocker, count=1)

    page = client_request.get(
        "main.view_notification",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    error_message = page.select_one("p.notification-status-cancelled").text
    assert normalize_spaces(error_message) == (
        "De validatie is mislukt omdat de inhoud buiten het afdrukbare gebied valt op pagina 1."
        "Bestanden moeten voldoen aan onze briefspecificatie (opent in een nieuw tabblad)."
    )


def test_should_show_image_of_templated_letter_notification_that_failed_validation_because_letter_is_too_long(
    client_request,
    mocker,
    fake_uuid,
):
    notification = create_notification(notification_status="validation-failed", template_type="letter")
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)
    do_mock_get_page_counts_for_letter(mocker, count=11)

    page = client_request.get(
        "main.view_notification",
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
    )

    error_message = page.select_one("p.notification-status-cancelled").text
    assert (
        normalize_spaces(error_message)
        == "De validatie is mislukt omdat deze brief 11 pagina’s lang is.Brieven mogen maximaal 10 pagina’s bevatten "
        "(5 dubbelzijdige vellen papier)."
    )


@pytest.mark.parametrize(
    "status, print_provider, expected_status",
    [
        ("created", None, "Wordt naar de printleverancier gestuurd"),
        ("sending", None, "Wordt naar de printleverancier gestuurd"),
        ("sent", "pingen", "Geaccepteerd door Pingen"),
        ("sent", "rest-endpoint", "Geaccepteerd door de printleverancier van uw organisatie"),
        ("delivered", "pingen", "Aan de post overgedragen"),
    ],
)
@freeze_time("2026-09-30 10:00")
def test_letter_notification_page_says_where_the_letter_is(
    client_request, mocker, fake_uuid, mock_get_page_counts_for_letter, status, print_provider, expected_status
):
    notification = create_notification(template_type="letter", notification_status=status)
    notification["print_provider"] = print_provider
    mocker.patch("app.notification_api_client.get_notification", return_value=notification)

    page = client_request.get("main.view_notification", service_id=SERVICE_ONE_ID, notification_id=fake_uuid)

    assert normalize_spaces(page.select_one("#letter-status").text) == expected_status
    # letters go to their print provider within minutes: no daily print run
    assert "17:30" not in page.text
