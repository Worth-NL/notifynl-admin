from unittest.mock import Mock

from flask import url_for
from requests import RequestException

from app.s3_client.s3_letter_upload_client import LetterMetadata
from tests.conftest import SERVICE_ONE_ID, do_mock_get_page_counts_for_letter


def test_post_upload_letter_shows_letter_preview_for_invalid_file(
    client_request,
    fake_uuid,
    mocker,
):
    letter_template = {
        "service": SERVICE_ONE_ID,
        "template_type": "letter",
        "reply_to_text": "",
        "postage": "netherlands",
        "subject": "hi",
        "content": "my letter",
        "is_precompiled_letter": True,
    }

    mocker.patch("uuid.uuid4", return_value=fake_uuid)
    mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mocker.patch("app.main.views_nl.uploads.upload_letter_to_s3")
    mock_sanitise_response = Mock()
    mock_sanitise_response.raise_for_status.side_effect = RequestException(response=Mock(status_code=400))
    mock_sanitise_response.json = lambda: {"message": "template preview error", "recipient_address": "The Queen"}
    mocker.patch("app.template_preview_client.sanitise_letter", return_value=mock_sanitise_response)
    mocker.patch("app.models.service.service_api_client.get_precompiled_template", return_value=letter_template)
    mocker.patch(
        "app.main.views_nl.uploads.get_letter_metadata",
        return_value=LetterMetadata(
            {
                "filename": "tests/test_pdf_files/one_page_pdf.pdf",
                "page_count": "1",
                "status": "invalid",
                "message": "template-preview-error",
            }
        ),
    )
    do_mock_get_page_counts_for_letter(mocker, count=1)

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.upload_letter",
            service_id=SERVICE_ONE_ID,
            _data={"file": file},
            _follow_redirects=True,
        )

    assert "The Queen" not in page.text
    assert len(page.select(".letter-postage")) == 0
    assert page.select_one("a.govuk-back-link")["href"] == f"/services/{SERVICE_ONE_ID}/upload-letter"
    assert page.select_one("input[type=file]")["data-button-text"]
    assert page.select_one("input[type=file]")["accept"] == ".pdf"

    letter_images = page.select("main img")
    assert len(letter_images) == 1
    assert letter_images[0]["src"] == url_for(
        ".view_letter_upload_as_preview", service_id=SERVICE_ONE_ID, file_id=fake_uuid, page=1
    )
