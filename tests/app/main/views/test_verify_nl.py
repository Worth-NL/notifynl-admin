import json

from itsdangerous import SignatureExpired

from tests.conftest import normalize_spaces


def test_verify_email_shows_flash_message_if_token_expired(
    client_request,
    mocker,
):
    client_request.logout()
    mocker.patch("app.main.views_nl.verify.check_token", side_effect=SignatureExpired("expired"))

    page = client_request.get(
        "main.verify_email",
        token="notreal",
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "De link in de e-mail die we u hebben gestuurd is verlopen. We hebben u een nieuwe gestuurd."
    )


def test_verify_email_redirects_to_sign_in_if_user_active(
    client_request,
    mocker,
    api_user_active,
    mock_send_verify_code,
):
    client_request.logout()
    token_data = {"user_id": api_user_active["id"], "secret_code": 12345}
    mocker.patch("app.main.views_nl.verify.check_token", return_value=json.dumps(token_data))

    page = client_request.get("main.verify_email", token="notreal", _follow_redirects=True)

    flash_banner = page.select_one("div.banner-dangerous").string.strip()
    assert flash_banner == "Deze bevestigingslink is verlopen."
