from io import BytesIO
from unittest.mock import Mock

import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.notify_client.messagebox_cpa_api_client_nl import CpaRejected
from tests.conftest import normalize_spaces

CLIENT = "app.main.views_nl.messagebox_cpas.messagebox_cpa_api_client"
PREPROD_HOST = "preprod-globe-ebms-internet.procesinfrastructuur.nl"
LIVE_HOST = "globe-ebms-internet.procesinfrastructuur.nl"

SUMMARY = {
    "cpa_id": "EXAMPLE-CPA",
    "status": "agreed",
    "start": "2026-11-05T00:00:00+00:00",
    "end": "2028-03-31T13:49:59+00:00",
    "parties": [
        {
            "name": "Logius",
            "party_ids": ["urn:osb:oin:22222222222222222222"],
            "endpoints": ["https://preprod-globe-ebms-internet.procesinfrastructuur.nl/ebXML"],
            "processes": ["MijnOverheid_BB_R"],
            "can_send": ["GLOBE-R-BV-Result"],
            "certificates": [],
        },
        {
            "name": "Example",
            "party_ids": ["urn:osb:oin:11111111111111111111"],
            "endpoints": ["https://ebms.example.invalid/ebms"],
            "processes": ["MijnOverheid_BB_R"],
            "can_send": ["GLOBE-R-BV-Request"],
            "certificates": [],
        },
    ],
}


def _assessment(purpose, eligible=True, warnings=()):
    return {
        "purpose": purpose,
        "eligible": eligible,
        "checks": [
            {"name": "own_endpoint", "passed": True, "message": "Our endpoint is https://ebms.example.invalid/ebms"},
            {
                "name": "counterparty_endpoint",
                "passed": eligible,
                "message": (
                    f"{PREPROD_HOST} is allowed for {purpose}"
                    if eligible
                    else f"{LIVE_HOST} isn't allowed for {purpose} (allowed: {PREPROD_HOST})"
                ),
            },
        ],
        "warnings": list(warnings),
    }


def _listing(cpa_id="EXAMPLE-CPA", selected_for=(), team=True, live=False):
    return {
        "cpa_id": cpa_id,
        "summary": {**SUMMARY, "cpa_id": cpa_id},
        "error": None,
        "assessments": {"live": _assessment("live", live), "team": _assessment("team", team)},
        "selected_for": list(selected_for),
    }


@pytest.fixture
def cpa_client(mocker):
    # an explicit MagicMock: patching the LocalProxy makes mock.patch build an AsyncMock
    client = mocker.MagicMock()
    mocker.patch(CLIENT, client)
    client.get_cpas.return_value = [_listing(selected_for=["team"])]
    client.get_selection.side_effect = lambda purpose: (
        {
            "purpose": "team",
            "cpa_id": "EXAMPLE-CPA",
            "message_type": "test-bericht",
            "updated_at": "2026-11-10T12:00:00",
            "updated_by_id": "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6",
        }
        if purpose == "team"
        else None
    )
    client.get_selection_history.return_value = []
    return client


@pytest.mark.parametrize(
    "endpoint, kwargs",
    [
        ("main.messagebox_cpas", {}),
        ("main.messagebox_cpa_upload", {}),
        ("main.messagebox_cpa_select", {"purpose": "team"}),
    ],
)
def test_messagebox_cpa_pages_are_platform_admin_only(client_request, cpa_client, endpoint, kwargs):
    client_request.get(endpoint, **kwargs, _expected_status=403)


@pytest.mark.parametrize(
    "endpoint, kwargs, data",
    [
        ("main.messagebox_cpa_upload_confirm", {}, {"cpa_xml": "<cpa/>", "purpose": "team"}),
        ("main.messagebox_cpa_select", {"purpose": "team"}, {"cpa_id": "EXAMPLE-CPA", "message_type": "bericht"}),
        ("main.messagebox_cpa_select_confirm", {"purpose": "live"}, {"cpa_id": "LIVE", "message_type": "bericht"}),
    ],
)
def test_messagebox_cpa_changes_are_platform_admin_only(client_request, cpa_client, endpoint, kwargs, data):
    client_request.post(endpoint, **kwargs, _data=data, _expected_status=403)

    cpa_client.upload_cpa.assert_not_called()
    cpa_client.select_cpa.assert_not_called()


def test_overview_shows_selections_and_cpas(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpas")

    rows = [normalize_spaces(row.text) for row in page.select("tbody tr")]
    assert rows[0].startswith("Live (productieomgeving van Logius) Instellingen van de omgeving")
    assert rows[1].startswith("Team (pre-productieomgeving van Logius) EXAMPLE-CPA BerichtType test-bericht")
    assert normalize_spaces(page.select_one("h3").text) == "EXAMPLE-CPA Team"
    assert "Live: niet bruikbaar, Team: bruikbaar" in normalize_spaces(page.text)
    assert "sinds 2026-11-10 13:00" in rows[1]
    assert "https://preprod-globe-ebms-internet.procesinfrastructuur.nl/ebXML" in normalize_spaces(page.text)
    assert page.select_one(f"a[href='{url_for('main.messagebox_cpa_upload')}']")
    assert "Berichtenbox-CPA’s" in normalize_spaces(page.select_one("nav.navigation").text)


def test_overview_shows_expiry_warnings(client_request, platform_admin_user, cpa_client):
    listing = _listing()
    listing["assessments"] = {
        purpose: _assessment(purpose, warnings=["The CPA ends on 2026-12-31"]) for purpose in ("live", "team")
    }
    cpa_client.get_cpas.return_value = [listing]
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpas")

    warnings = [normalize_spaces(warning.text) for warning in page.select(".govuk-warning-text")]
    assert warnings == ["! Waarschuwing De CPA loopt af op 2026-12-31"]


def test_upload_validates_and_shows_the_checks_before_uploading(client_request, platform_admin_user, cpa_client):
    cpa_client.validate_cpa.return_value = {"summary": SUMMARY, "assessment": _assessment("team")}
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO(b"<cpa/>"), "cpa.xml")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    cpa_client.validate_cpa.assert_called_once_with("<cpa/>", "team")
    cpa_client.upload_cpa.assert_not_called()
    checks = [normalize_spaces(item.text) for item in page.select("main ul.govuk-list li")]
    assert f"✓ Geslaagd: {PREPROD_HOST} is toegestaan voor team" in checks
    assert page.select_one("input[name=cpa_xml]")["value"] == "<cpa/>"
    assert page.select_one("input[name=purpose]")["value"] == "team"
    assert page.select_one("form")["action"] == url_for("main.messagebox_cpa_upload_confirm")


def test_upload_check_offers_no_upload_for_an_ineligible_cpa(client_request, platform_admin_user, cpa_client):
    cpa_client.validate_cpa.return_value = {"summary": SUMMARY, "assessment": _assessment("team", eligible=False)}
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO(b"<cpa/>"), "cpa.xml")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    assert f"✗ Mislukt: {LIVE_HOST} is niet toegestaan voor team (toegestaan: {PREPROD_HOST})" in normalize_spaces(
        page.text
    )
    assert not page.select_one("input[name=cpa_xml]")


def test_upload_shows_why_a_cpa_cannot_be_read(client_request, platform_admin_user, cpa_client):
    cpa_client.validate_cpa.side_effect = CpaRejected("Expected a CollaborationProtocolAgreement")
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO(b"<x/>"), "cpa.xml")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    assert "Expected a CollaborationProtocolAgreement" in normalize_spaces(page.select_one(".govuk-error-summary").text)
    assert not page.select_one("input[name=cpa_xml]")


def test_upload_rejects_a_non_xml_file(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO(b"x"), "cpa.txt")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    assert "Kies een XML-bestand" in normalize_spaces(page.text)
    cpa_client.validate_cpa.assert_not_called()


def test_upload_confirm_uploads_and_redirects(client_request, platform_admin_user, cpa_client):
    cpa_client.upload_cpa.return_value = {"summary": SUMMARY, "assessment": _assessment("team")}
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_upload_confirm",
        _data={"cpa_xml": "<cpa/>", "purpose": "team"},
        _expected_redirect=url_for("main.messagebox_cpas"),
    )

    cpa_client.upload_cpa.assert_called_once_with("<cpa/>", "team")


def test_upload_confirm_shows_the_api_refusal(client_request, platform_admin_user, cpa_client):
    cpa_client.upload_cpa.side_effect = CpaRejected("ebms-core already has a CPA with id EXAMPLE-CPA")
    cpa_client.validate_cpa.return_value = {"summary": SUMMARY, "assessment": _assessment("team")}
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload_confirm", _data={"cpa_xml": "<cpa/>", "purpose": "team"}, _expected_status=200
    )

    assert "ebms-core heeft al een CPA met id EXAMPLE-CPA" in normalize_spaces(
        page.select_one(".govuk-error-summary").text
    )
    assert not page.select_one("input[name=cpa_xml]")


def test_upload_confirm_refuses_an_unknown_purpose(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_upload_confirm", _data={"cpa_xml": "<cpa/>", "purpose": "other"}, _expected_status=400
    )

    cpa_client.upload_cpa.assert_not_called()


def test_select_offers_only_eligible_cpas(client_request, platform_admin_user, cpa_client):
    cpa_client.get_cpas.return_value = [_listing("PREPROD", team=True), _listing("LIVE", team=False, live=True)]
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpa_select", purpose="team")

    assert [radio["value"] for radio in page.select("input[name=cpa_id]")] == ["PREPROD"]
    assert page.select_one("input[name=message_type]")["value"] == "test-bericht"


def test_select_team_selects_directly(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_select",
        purpose="team",
        _data={"cpa_id": "EXAMPLE-CPA", "message_type": "test-bericht"},
        _expected_redirect=url_for("main.messagebox_cpas"),
    )

    cpa_client.select_cpa.assert_called_once_with("team", "EXAMPLE-CPA", "test-bericht", platform_admin_user["id"])


def test_select_shows_the_api_refusal(client_request, platform_admin_user, cpa_client):
    cpa_client.select_cpa.side_effect = CpaRejected(
        "The CPA can't be used for team",
        {"checks": [{"name": "period", "passed": False, "message": "Not valid today"}]},
    )
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_select",
        purpose="team",
        _data={"cpa_id": "EXAMPLE-CPA", "message_type": "test-bericht"},
        _expected_status=200,
    )

    assert "De CPA kan niet worden gebruikt voor team Not valid today" in normalize_spaces(
        page.select_one(".govuk-error-message").text
    )


def test_select_live_asks_for_confirmation_first(client_request, platform_admin_user, cpa_client):
    cpa_client.get_cpas.return_value = [_listing("LIVE", team=False, live=True)]
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_select",
        purpose="live",
        _data={"cpa_id": "LIVE", "message_type": "bericht"},
        _expected_status=200,
    )

    cpa_client.select_cpa.assert_not_called()
    assert normalize_spaces(page.select_one("h1").text) == "Live-CPA wijzigen"
    assert "berichtenboxberichten van burgers" in normalize_spaces(page.select_one(".govuk-warning-text").text)
    assert page.select_one("form")["action"] == url_for("main.messagebox_cpa_select_confirm", purpose="live")
    assert page.select_one("input[name=cpa_id]")["value"] == "LIVE"


def test_select_confirm_selects_live(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_select_confirm",
        purpose="live",
        _data={"cpa_id": "LIVE", "message_type": "bericht"},
        _expected_redirect=url_for("main.messagebox_cpas"),
    )

    cpa_client.select_cpa.assert_called_once_with("live", "LIVE", "bericht", platform_admin_user["id"])


def test_select_unknown_purpose_is_404(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    client_request.get_url("/platform-admin/messagebox-cpas/other/select", _expected_status=404)


def test_overview_still_shows_the_selections_when_ebms_core_is_unreachable(
    client_request, platform_admin_user, cpa_client
):
    cpa_client.get_cpas.side_effect = HTTPError(response=Mock(status_code=502))
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpas")

    rows = [normalize_spaces(row.text) for row in page.select("tbody tr")]
    assert rows[1].startswith("Team (pre-productieomgeving van Logius) EXAMPLE-CPA")
    assert "ebms-core is nu niet bereikbaar" in normalize_spaces(page.select_one(".govuk-inset-text").text)
    assert "ebms-core heeft geen CPA’s" not in normalize_spaces(page.text)


def test_overview_shows_a_cpa_ebms_core_cannot_return(client_request, platform_admin_user, cpa_client):
    cpa_client.get_cpas.return_value = [
        {**_listing("GONE"), "summary": None, "assessments": {}, "error": "ebms-core can't return the CPA: 404"},
        _listing("PREPROD"),
    ]
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpas")

    assert "Kan deze CPA niet lezen: ebms-core kan de CPA niet teruggeven: 404" in normalize_spaces(page.text)
    assert [normalize_spaces(h3.text) for h3 in page.select("h3")] == ["GONE", "PREPROD"]


def test_select_says_ebms_core_is_unreachable(client_request, platform_admin_user, cpa_client):
    cpa_client.get_cpas.side_effect = HTTPError(response=Mock(status_code=502))
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpa_select", purpose="team")

    assert not page.select("input[name=cpa_id]")
    assert "ebms-core is nu niet bereikbaar" in normalize_spaces(page.select_one(".govuk-inset-text").text)


def test_overview_raises_other_api_errors(client_request, platform_admin_user, cpa_client):
    cpa_client.get_cpas.side_effect = HTTPError(response=Mock(status_code=400))
    client_request.login(platform_admin_user)

    client_request.get("main.messagebox_cpas", _expected_status=500, _test_page_title=False)


def test_select_shows_where_each_cpa_sends_and_how_long_it_is_valid(client_request, platform_admin_user, cpa_client):
    listing = _listing("PREPROD")
    listing["assessments"]["team"]["warnings"] = ["The CPA ends on 2028-03-31"]
    cpa_client.get_cpas.return_value = [listing]
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpa_select", purpose="team")

    assert normalize_spaces(page.select_one(".govuk-radios__hint").text) == (
        f"Logius: {PREPROD_HOST}; Example: ebms.example.invalid. Geldig van 2026-11-05 tot 2028-03-31. "
        "De CPA loopt af op 2028-03-31"
    )


def test_select_refuses_a_message_type_the_api_cannot_store(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_select",
        purpose="team",
        _data={"cpa_id": "EXAMPLE-CPA", "message_type": "x" * 256},
        _expected_status=200,
    )

    assert "niet langer zijn dan 255 tekens" in normalize_spaces(page.select_one(".govuk-error-message").text)
    cpa_client.select_cpa.assert_not_called()


def test_select_live_confirmation_shows_the_chosen_cpa(client_request, platform_admin_user, cpa_client):
    listing = _listing("LIVE", team=False, live=True)
    listing["assessments"]["live"]["warnings"] = ["The CPA ends on 2028-03-31"]
    cpa_client.get_cpas.return_value = [listing]
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_select",
        purpose="live",
        _data={"cpa_id": "LIVE", "message_type": "bericht"},
        _expected_status=200,
    )

    text = normalize_spaces(page.text)
    assert "De CPA loopt af op 2028-03-31" in text
    assert f"Endpoint: https://{PREPROD_HOST}/ebXML" in text
    assert "2026-11-05 tot 2028-03-31" in text


def test_select_confirm_shows_the_api_refusal_on_the_select_page(client_request, platform_admin_user, cpa_client):
    cpa_client.select_cpa.side_effect = CpaRejected("ebms-core has no CPA with id LIVE")
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_select_confirm",
        purpose="live",
        _data={"cpa_id": "LIVE", "message_type": "bericht"},
        _expected_redirect=url_for("main.messagebox_cpa_select", purpose="live"),
    )

    page = client_request.get("main.messagebox_cpa_select", purpose="live")
    assert "ebms-core heeft geen CPA met id LIVE" in normalize_spaces(page.text)


def test_select_history_shows_who_selected(client_request, platform_admin_user, cpa_client):
    cpa_client.get_selection_history.return_value = [
        {
            "purpose": "team",
            "cpa_id": "EXAMPLE-CPA",
            "message_type": "test-bericht",
            "updated_at": "2026-07-01T10:00:00.000000Z",
            "updated_by_id": platform_admin_user["id"],
        }
    ]
    client_request.login(platform_admin_user)

    page = client_request.get("main.messagebox_cpa_select", purpose="team")

    cells = [normalize_spaces(cell.text) for cell in page.select("tbody tr td")]
    assert cells == ["2026-07-01 12:00", "EXAMPLE-CPA", "test-bericht", "Platform admin user"]


def test_upload_reads_a_utf8_file_with_a_byte_order_mark(client_request, platform_admin_user, cpa_client):
    cpa_client.validate_cpa.return_value = {"summary": SUMMARY, "assessment": _assessment("team")}
    client_request.login(platform_admin_user)

    client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO("\ufeff<cpa/>".encode()), "cpa.xml")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    cpa_client.validate_cpa.assert_called_once_with("<cpa/>", "team")


def test_upload_rejects_a_file_that_is_not_utf8(client_request, platform_admin_user, cpa_client):
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload",
        _data={"purpose": "team", "file": (BytesIO(b"<cpa>\xff</cpa>"), "cpa.xml")},
        _content_type="multipart/form-data",
        _expected_status=200,
    )

    assert "Het bestand is geen UTF-8 XML" in normalize_spaces(page.text)
    cpa_client.validate_cpa.assert_not_called()


def test_upload_confirm_shows_the_checks_from_the_refusal_without_validating_again(
    client_request, platform_admin_user, cpa_client
):
    cpa_client.upload_cpa.side_effect = CpaRejected(
        "The CPA can't be used for team", _assessment("team", eligible=False), SUMMARY
    )
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.messagebox_cpa_upload_confirm", _data={"cpa_xml": "<cpa/>", "purpose": "team"}, _expected_status=200
    )

    cpa_client.validate_cpa.assert_not_called()
    assert "De CPA kan niet worden gebruikt voor team" in normalize_spaces(page.select_one(".govuk-error-summary").text)
    assert f"✗ Mislukt: {LIVE_HOST} is niet toegestaan voor team" in normalize_spaces(page.text)


def test_select_history_names_a_deleted_user_unknown(client_request, platform_admin_user, cpa_client, mocker):
    def get_user(user_id):
        if user_id == platform_admin_user["id"]:
            return platform_admin_user
        raise HTTPError(response=Mock(status_code=404))

    client_request.login(platform_admin_user)
    mocker.patch("app.user_api_client.get_user", side_effect=get_user)
    cpa_client.get_selection_history.return_value = [
        {
            "purpose": "team",
            "cpa_id": "EXAMPLE-CPA",
            "message_type": "test-bericht",
            "updated_at": "2026-07-01T10:00:00.000000Z",
            "updated_by_id": "11111111-1111-1111-1111-111111111111",
        }
    ]

    page = client_request.get("main.messagebox_cpa_select", purpose="team")

    assert normalize_spaces(page.select("tbody tr td")[-1].text) == "Onbekende gebruiker"
