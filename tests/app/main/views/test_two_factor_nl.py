import logging
from unittest.mock import PropertyMock

import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def mock_email_validated_recently(mocker):
    return mocker.patch("app.models.user.User.email_needs_revalidating", new_callable=PropertyMock, return_value=False)


@pytest.mark.parametrize("new_password", ["just-a-string", b"bytes-string"])
def test_two_factor_sms_should_return_error_if_new_password_not_encrypted(
    client_request,
    api_user_active,
    mock_update_user_password,
    mock_email_validated_recently,
    caplog,
    new_password,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session["user_details"] = {
            "id": api_user_active["id"],
            "email": api_user_active["email_address"],
            "new_password": new_password,
        }
    with caplog.at_level(logging.WARNING):
        page = client_request.post(
            "main.two_factor_sms",
            _data={"sms_code": "12345"},
            _follow_redirects=True,
        )

    assert "Error during new password decryption for user id 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6" in caplog.messages

    assert page.select_one("h1").string == "Inloggen"
    assert page.select_one(".banner-dangerous").text.strip() == (
        "There was a problem with your password. Please try again."
    )

    mock_update_user_password.assert_not_called()


def test_two_factor_sms_should_return_error_if_new_password_encrypted_with_wrong_key(
    client_request, api_user_active, mock_update_user_password, mock_email_validated_recently, caplog
):
    client_request.logout()

    wrong_key_fernet = Fernet(Fernet.generate_key())

    with client_request.session_transaction() as session:
        session["user_details"] = {
            "id": api_user_active["id"],
            "email": api_user_active["email_address"],
            "new_password": wrong_key_fernet.encrypt(b"changedpassword"),
        }
    with caplog.at_level(logging.WARNING):
        page = client_request.post(
            "main.two_factor_sms",
            _data={"sms_code": "12345"},
            _follow_redirects=True,
        )

    assert "Error during new password decryption for user id 6ce466d0-fd6a-11e5-82f5-e0accb9d11a6" in caplog.messages

    assert page.select_one("h1").string == "Inloggen"
    assert page.select_one(".banner-dangerous").text.strip() == (
        "There was a problem with your password. Please try again."
    )

    mock_update_user_password.assert_not_called()
