from tests.conftest import normalize_spaces


def test_registration_continue_page(client_request, fake_uuid):
    with client_request.session_transaction() as session:
        session["user_details"] = {"email": "user@gov.uk", "id": fake_uuid}

    page = client_request.get("main.registration_continue")

    assert normalize_spaces(page.select_one("h1").text) == "Controleer uw inbox"
    assert "We hebben een e-mail gestuurd naar user@gov.uk" in page.text
