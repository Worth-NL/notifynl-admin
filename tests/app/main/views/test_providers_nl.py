from tests.app.main.views.test_providers import provider_json
from tests.conftest import normalize_spaces


def test_view_providers_lists_the_letter_providers_read_only(client_request, platform_admin_user, mocker):
    providers = [
        provider_json({"id": "sms-1", "identifier": "spryng", "display_name": "Spryng"}),
        provider_json({"id": "email-1", "identifier": "ses", "display_name": "AWS SES", "notification_type": "email"}),
        provider_json({"id": "letter-1", "identifier": "dvla", "display_name": "DVLA", "notification_type": "letter"}),
        provider_json(
            {"id": "letter-2", "identifier": "pingen", "display_name": "Pingen", "notification_type": "letter"}
        ),
        provider_json(
            {
                "id": "letter-3",
                "identifier": "rest-endpoint",
                "display_name": "REST-endpoint",
                "notification_type": "letter",
            }
        ),
    ]
    mocker.patch("app.provider_client.get_all_providers", return_value={"provider_details": providers})
    client_request.login(platform_admin_user)

    page = client_request.get("main.view_providers")

    assert "Brieven" in [normalize_spaces(h2.text) for h2 in page.select("main h2")]
    letter_table = page.select("table")[-1]
    assert [normalize_spaces(row.select_one("td").text) for row in letter_table.select("tbody tr")] == [
        "DVLA",
        "Pingen",
        "REST-endpoint",
    ]
    # chosen per organisation: nothing to edit here
    assert not letter_table.select("a")
    # the SMS and email tables don't list letter providers
    for table in page.select("table")[:-1]:
        assert "Pingen" not in normalize_spaces(table.text)
