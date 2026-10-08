import json


def test_complete_register_flashes_dutch_confirmation(client_request, platform_admin_user, mocker):
    with client_request.session_transaction() as session:
        session["webauthn_registration_state"] = "state"

    mocker.patch("app.user_api_client.create_webauthn_credential_for_user")
    mocker.patch("app.models.webauthn_credential.WebAuthnCredential.from_registration")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.webauthn_complete_register",
        _data=json.dumps("public_key_credential"),
        _content_type="application/json",
        _expected_status=200,
    )

    with client_request.session_transaction() as session:
        assert "webauthn_registration_state" not in session
        assert session["_flashes"] == [
            (
                "default_with_tick",
                "Registratie voltooid. De volgende keer dat u inlogt bij Notify, "
                "wordt u gevraagd uw beveiligingssleutel te gebruiken.",
            )
        ]
