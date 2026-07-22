from tests.conftest import SERVICE_ONE_ID, create_notification, normalize_spaces


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
