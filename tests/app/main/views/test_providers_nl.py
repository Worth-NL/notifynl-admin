def test_view_provider_shows_reason_column_in_dutch(client_request, platform_admin_user, mocker):
    history = {
        "data": [
            {
                "id": "f9af1ec7-58ef-4f7d-a6f4-5fe7e48644cb",
                "active": True,
                "priority": 20,
                "display_name": "Spryng",
                "identifier": "spryng",
                "notification_type": "sms",
                "updated_at": None,
                "version": 2,
                "reason": "Storing bij Firetext",
                "created_by": {
                    "email_address": "test@example.nl",
                    "name": "Test Gebruiker",
                    "id": "7cc1dddb-bcbc-4739-8fc1-61bedde3332a",
                },
                "supports_international": False,
            },
            {
                "id": "f9af1ec7-58ef-4f7d-a6f4-5fe7e48644cb",
                "active": True,
                "priority": 10,
                "display_name": "Spryng",
                "identifier": "spryng",
                "notification_type": "sms",
                "updated_at": None,
                "version": 1,
                "reason": None,
                "created_by": None,
                "supports_international": False,
            },
        ]
    }
    mocker.patch("app.provider_client.get_provider_versions", return_value=history)
    client_request.login(platform_admin_user)

    page = client_request.get("main.view_provider", provider_id=history["data"][0]["id"])

    table_rows = page.select("table tr")
    assert [th.text.strip() for th in table_rows[0].select("th")] == [
        "Versie",
        "Laatst bijgewerkt",
        "Bijgewerkt door",
        "Prioriteit",
        "Actief",
        "Reden",
    ]
    assert table_rows[1].select("td")[-1].text.strip() == "Storing bij Firetext"
    assert table_rows[2].select("td")[-1].text.strip() == "Niet opgegeven"
