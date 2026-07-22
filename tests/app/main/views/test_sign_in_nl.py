from app.models.user import User


def test_should_return_locked_out_true_when_user_is_locked(
    client_request,
    mock_get_user_by_email_locked,
):
    client_request.logout()
    page = client_request.post(
        "main.sign_in",
        _data={
            "email_address": "valid@example.gov.uk",
            "password": "whatIsMyPassword!",
        },
        _expected_status=200,
    )
    assert "Het e-mailadres of wachtwoord dat u heeft ingevoerd is onjuist" in page.text


def test_should_return_200_when_user_does_not_exist(
    client_request,
    mock_get_user_by_email_not_found,
):
    client_request.logout()
    page = client_request.post(
        "main.sign_in",
        _data={"email_address": "notfound@gov.uk", "password": "doesNotExist!"},
        _expected_status=200,
    )

    assert "Het e-mailadres of wachtwoord dat u heeft ingevoerd is onjuist" in page.text


def test_when_signing_in_as_invited_user_you_cannot_accept_an_invite_for_another_email_address(
    client_request,
    mocker,
    mock_verify_password,
    api_user_active,
    sample_invite,
    mock_accept_invite,
    mock_send_verify_code,
    mock_get_invited_user_by_id,
):
    sample_invite["email_address"] = "some_other_user@user.gov.uk"

    mocker.patch(
        "app.models.user.User.from_email_address_and_password_or_none",
        return_value=User(api_user_active),
    )

    client_request.logout()

    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]

    page = client_request.post(
        "main.sign_in", _data={"email_address": "test@user.gov.uk", "password": "val1dPassw0rd!"}, _expected_status=403
    )

    assert mock_accept_invite.called is False
    assert mock_send_verify_code.called is False
    assert page.select_one(".banner-dangerous").text.strip() == "U kunt geen uitnodiging voor iemand anders accepteren."
