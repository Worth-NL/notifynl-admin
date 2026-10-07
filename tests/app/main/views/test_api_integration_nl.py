import uuid

from freezegun import freeze_time

from tests.conftest import SERVICE_ONE_ID, create_user, normalize_spaces


@freeze_time("2026-09-14 12:00")
def test_should_show_api_keys_page_nl(
    client_request,
    mock_get_api_keys,
    mock_get_users_by_service,
    api_user_active,
    mocker,
):
    mocker.patch(
        "app.user_api_client.get_user",
        side_effect=[
            api_user_active,
            create_user(id=str(uuid.uuid4()), name="Gearchiveerde gebruiker", state="inactive"),
        ],
    )

    page = client_request.get("main.api_keys", service_id=SERVICE_ONE_ID)

    keys = {normalize_spaces(key.select_one(".api-key__name").text): key for key in page.select("li.api-key")}
    assert set(keys) == {"some key name", "another key name", "third key"}

    # The revoke link's accessible name stays "Intrekken <key name>" (as before the summary-list redesign)
    assert [normalize_spaces(link.text) for link in page.select("a.api-key__action-link")] == [
        "Intrekken some key name",
        "Intrekken third key",
    ]

    assert "Ingetrokken op" in normalize_spaces(keys["another key name"].select_one(".api-key__revoked").text)
    assert normalize_spaces(keys["some key name"].select_one(".api-key__type").text) == "Live – verzendt naar iedereen"
    assert normalize_spaces(keys["another key name"].select_one(".api-key__type").text) == (
        "Test – simuleert het verzenden van berichten"
    )
    assert normalize_spaces(keys["third key"].select_one(".api-key__type").text) == (
        "Team en gastenlijst – beperkt wie u kunt benaderen"
    )
