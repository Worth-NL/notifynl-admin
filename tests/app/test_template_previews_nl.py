from unittest.mock import Mock

import pytest

from app import template_preview_client
from app.models.branding import LetterBranding
from app.models.service import Service


@pytest.mark.parametrize("letter_address_placement", ["50mm", "60mm"])
def test_get_preview_for_templated_letter_includes_letter_address_placement(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
    letter_address_placement,
):
    mocker.patch(
        "app.template_preview_client.requests_session.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )
    service = mocker.Mock(
        spec=Service,
        letter_branding=LetterBranding({"filename": "hm-government"}),
        letter_address_placement=letter_address_placement,
    )
    template = mock_get_service_letter_template("123", "456")["data"]

    template_preview_client.get_preview_for_templated_letter(db_template=template, filetype="png", service=service)

    request_mock = template_preview_client.requests_session.post
    assert request_mock.call_args[1]["json"]["letter_address_placement"] == letter_address_placement


def test_get_preview_for_templated_letter_letter_address_placement_is_none_without_service(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_onwards_request_headers,
):
    mocker.patch(
        "app.template_preview_client.requests_session.post",
        return_value=Mock(content="a", status_code="b", headers={"content-type": "image/png"}),
    )
    template = mock_get_service_letter_template("123", "456")["data"]

    template_preview_client.get_preview_for_templated_letter(db_template=template, filetype="png")

    request_mock = template_preview_client.requests_session.post
    assert request_mock.call_args[1]["json"]["letter_address_placement"] is None
