from tests.conftest import normalize_spaces


def test_trial_mode_sending_limits(client_request):
    page = client_request.get("main.guidance_trial_mode")

    assert normalize_spaces("Er is een dagelijkse limiet van 50 e-mails en 50 SMS-berichten.") in page.text


def test_letter_spec_pdf_is_not_offered(client_request):
    # [NOTIFYNL] NL has no generic letter specification PDF, so neither the redirect nor the link exist
    client_request.logout()
    client_request.get_url("/docs/notify-pdf-letter-spec-latest.pdf", _expected_status=404)

    page = client_request.get("main.guidance_upload_a_letter")
    assert "pdf-letter-spec" not in str(page)
    assert "brievenspecificatie als PDF" not in normalize_spaces(page.text)
