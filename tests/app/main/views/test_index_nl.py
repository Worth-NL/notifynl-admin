from tests.conftest import normalize_spaces


def test_trial_mode_sending_limits(client_request):
    page = client_request.get("main.guidance_trial_mode")

    assert normalize_spaces("Er is een dagelijkse limiet van 50 e-mails en 50 SMS-berichten.") in page.text
