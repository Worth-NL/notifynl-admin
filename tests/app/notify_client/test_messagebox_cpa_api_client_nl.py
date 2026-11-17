import json
from unittest.mock import Mock

import pytest
from notifications_python_client.errors import HTTPError

from app.notify_client.messagebox_cpa_api_client_nl import CpaRejected, MessageboxCpaApiClient

BASE = "app.notify_client.messagebox_cpa_api_client_nl.MessageboxCpaApiClient"
USER_ID = "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


@pytest.fixture
def client(notify_admin):
    return MessageboxCpaApiClient(notify_admin)


def _http_error(status_code, body=None, text=None):
    response = Mock(status_code=status_code)
    if body is not None:
        response.json.return_value = body
    else:
        response.json.side_effect = json.JSONDecodeError("Expecting value", text or "", 0)
    return HTTPError(response=response)


@pytest.mark.parametrize(
    "method, args, url",
    [
        ("get_cpas", (), "/platform-admin/messagebox/cpas"),
        ("get_selection", ("team",), "/platform-admin/messagebox/selection/team"),
        ("get_selection_history", ("live",), "/platform-admin/messagebox/selection/live/history"),
    ],
)
def test_reads(client, mocker, method, args, url):
    mock_get = mocker.patch(f"{BASE}.get", return_value={"data": "result"})

    assert getattr(client, method)(*args) == "result"
    mock_get.assert_called_once_with(url)


@pytest.mark.parametrize(
    "method, args, url, data",
    [
        (
            "validate_cpa",
            ("<cpa/>", "team"),
            "/platform-admin/messagebox/cpas/validate",
            {"cpa_xml": "<cpa/>", "purpose": "team"},
        ),
        ("upload_cpa", ("<cpa/>", "live"), "/platform-admin/messagebox/cpas", {"cpa_xml": "<cpa/>", "purpose": "live"}),
        (
            "select_cpa",
            ("team", "EXAMPLE-CPA", "bericht", USER_ID),
            "/platform-admin/messagebox/selection/team",
            {"cpa_id": "EXAMPLE-CPA", "message_type": "bericht", "updated_by_id": USER_ID},
        ),
    ],
)
def test_writes(client, mocker, method, args, url, data):
    mock_post = mocker.patch(f"{BASE}.post", return_value={"data": "result"})

    assert getattr(client, method)(*args) == "result"
    mock_post.assert_called_once_with(url, data=data)


@pytest.mark.parametrize(
    "method, args",
    [
        ("validate_cpa", ("<cpa/>", "team")),
        ("upload_cpa", ("<cpa/>", "team")),
        ("select_cpa", ("team", "EXAMPLE-CPA", "bericht", USER_ID)),
    ],
)
def test_a_guardrail_refusal_becomes_cpa_rejected(client, mocker, method, args):
    body = {"result": "error", "message": "The CPA can't be used for team", "assessment": {"checks": []}, "summary": {}}
    mocker.patch(f"{BASE}.post", side_effect=_http_error(400, body))

    with pytest.raises(CpaRejected) as e:
        getattr(client, method)(*args)

    assert e.value.message == "The CPA can't be used for team"
    assert e.value.assessment == {"checks": []}
    assert e.value.summary == {}


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            _http_error(400, {"status_code": 400, "errors": [{"error": "ValidationError", "message": "too long"}]}),
            id="schema error without a message",
        ),
        pytest.param(_http_error(400, text="<html>Bad Request</html>"), id="400 that isn't JSON"),
        pytest.param(_http_error(502, {"result": "error", "message": "ebms-core couldn't handle it"}), id="502"),
        pytest.param(_http_error(500, {"result": "error", "message": "Internal server error"}), id="500"),
    ],
)
def test_other_errors_stay_http_errors(client, mocker, error):
    mocker.patch(f"{BASE}.post", side_effect=error)

    with pytest.raises(HTTPError) as e:
        client.validate_cpa("<cpa/>", "team")

    assert e.value is error
