from flask import url_for

# Covers the "main.add_service" gov-user page skipped in test_add_service.py::
# test_gov_user_can_see_trial_mode_guidance_page (reason: "[NOTIFYNL] email_domains.txt
# change breaks this.") - the fixture user's email is switched to a real domain from
# email_domains.txt so `is_gov_user` resolves True via the static check, same as it did
# upstream via "gov.uk".


def test_gov_user_can_see_trial_mode_guidance_page(
    client_request,
    api_user_active,
    mock_get_organisations,
    mock_get_organisations_and_services_for_user,
):
    api_user_active["email_address"] = "test@amsterdam.nl"
    client_request.login(api_user_active)
    page = client_request.get("main.add_service")
    continue_button = page.select_one("main a.govuk-button")
    assert page.select_one("h1").text.strip() == "Uw dienst start in proefmodus"
    assert continue_button["href"] == url_for(".name_service")
