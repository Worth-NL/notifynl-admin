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


def test_message_status_spam_advice_links_to_ncsc(client_request):
    # [NOTIFYNL] NCSC phishing signs instead of the GOV.UK service manual
    client_request.logout()
    page = client_request.get("main.guidance_message_status", notification_type="email")

    link = page.select_one("a[href='https://www.ncsc.nl/phishing/hoe-herken-ik-een-phishing-e-mail']")
    assert normalize_spaces(link.text) == "Controleer of uw inhoud niet op spam lijkt"
    assert "gov.uk" not in str(page.select_one("main"))


def test_design_content_redirects_to_ncsc(client_request):
    client_request.logout()
    client_request.get_url(
        "/design-patterns-content-guidance",
        _expected_status=301,
        _expected_redirect="https://www.ncsc.nl/phishing/hoe-herken-ik-een-phishing-e-mail",
    )


def test_letter_spec_address_block_matches_nl_address_windows(client_request):
    # [NOTIFYNL] template-preview validates the address at 50mm or 60mm from the top, 40mm high
    client_request.logout()
    page = normalize_spaces(client_request.get("main.guidance_upload_a_letter").text)

    assert "Positie: 24,6 mm vanaf de linkerkant, 50 mm of 60 mm vanaf de bovenkant" in page
    assert "Afmeting: 95,4 mm breed bij 40 mm hoog" in page
    assert "Adresplaatsing op de brief" in page
    assert "39,5 mm" not in page
