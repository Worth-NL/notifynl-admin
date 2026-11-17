import uuid

import pytest
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


LIVE_KEY = "Live – verstuurt naar iedereen"
TEAM_KEY = "Team en gastenlijst – beperkt naar wie je kunt sturen"
TEST_KEY = "Test – simuleert het versturen van berichten"
LETTER_HINT = "Brieven worden niet verstuurd, alleen gesimuleerd."
MESSAGEBOX_HINT = (
    "Berichtenboxberichten gaan naar de pre-productieomgeving van Logius en werken alleen met test-BSN’s van Logius."
)


@pytest.mark.parametrize(
    "restricted, permissions, expected_options",
    [
        (
            True,
            [],
            [(LIVE_KEY, "Niet beschikbaar omdat uw dienst in test modus is"), TEAM_KEY, TEST_KEY],
        ),
        (False, [], [LIVE_KEY, TEAM_KEY, TEST_KEY]),
        (False, ["letter"], [LIVE_KEY, (TEAM_KEY, LETTER_HINT), TEST_KEY]),
        (False, ["messagebox"], [LIVE_KEY, (TEAM_KEY, MESSAGEBOX_HINT), TEST_KEY]),
        (False, ["letter", "messagebox"], [LIVE_KEY, (TEAM_KEY, f"{LETTER_HINT} {MESSAGEBOX_HINT}"), TEST_KEY]),
    ],
)
def test_should_show_create_api_key_page(
    client_request,
    mocker,
    mock_get_api_keys,
    restricted,
    permissions,
    expected_options,
    service_one,
):
    service_one["restricted"] = restricted
    service_one["permissions"] = [
        permission for permission in service_one["permissions"] if permission not in {"letter", "messagebox"}
    ] + permissions
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    page = client_request.get("main.create_api_key", service_id=SERVICE_ONE_ID)

    items = page.select(".govuk-radios__item")
    assert len(items) == len(expected_options)
    for item, option in zip(items, expected_options, strict=True):
        label, hint = option if isinstance(option, tuple) else (option, None)
        assert normalize_spaces(item.select_one(".govuk-label").text) == label
        assert (
            normalize_spaces(item.select_one(".govuk-hint").text) if item.select_one(".govuk-hint") else None
        ) == hint
