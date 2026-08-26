from unittest.mock import Mock

import pytest
from flask import make_response, url_for
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


def test_post_upload_letter_shows_letter_preview_for_valid_file(
    active_user_with_permissions,
    service_one,
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
    mocker.patch(
        "app.template_preview_client.sanitise_letter",
        return_value=Mock(
            content="The sanitised content",
            json=lambda: {"file": "VGhlIHNhbml0aXNlZCBjb250ZW50", "recipient_address": "The Queen"},
        ),
    )
    mocker.patch("app.main.views_nl.uploads.upload_letter_to_s3")
    mocker.patch("app.main.views_nl.uploads.backup_original_letter_to_s3")
    mocker.patch("app.main.views_nl.uploads.pdf_page_count", return_value=3)
    do_mock_get_page_counts_for_letter(mocker, count=3)
    mocker.patch(
        "app.main.views_nl.uploads.get_letter_metadata",
        return_value=LetterMetadata(
            {
                "filename": "tests/test_pdf_files/one_page_pdf.pdf",
                "page_count": "3",
                "status": "valid",
                "recipient": "The Queen",
            }
        ),
    )
    mocker.patch("app.models.service.service_api_client.get_precompiled_template", return_value=letter_template)

    service_one["restricted"] = False
    client_request.login(active_user_with_permissions, service=service_one)

    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.upload_letter",
            service_id=SERVICE_ONE_ID,
            _data={"file": file},
            _follow_redirects=True,
        )

    assert page.select_one("h1").text == "tests/test_pdf_files/one_page_pdf.pdf"
    assert len(page.select(".letter-postage")) == 0
    # Check postage radios exists and netherlands is checked by default
    assert page.select_one("input#postage-0[checked]")["value"] == "netherlands"
    assert page.select_one("input#postage-1")["value"] == "europe"
    assert page.select_one("input#postage-2")["value"] == "rest-of-world"

    letter_images = page.select("main img")
    assert len(letter_images) == 3

    for page_no, img in enumerate(letter_images, start=1):
        assert img["src"] == url_for(
            ".view_letter_upload_as_preview", service_id=SERVICE_ONE_ID, file_id=fake_uuid, page=page_no
        )


@pytest.mark.parametrize(
    "invalid_pages, page_requested, overlay_expected",
    (
        ("[1, 2]", 1, True),
        ("[1, 2]", 2, True),
        ("[1, 2]", 3, False),
        ("[]", 1, False),
    ),
)
def test_uploaded_letter_preview_image_shows_overlay_when_content_outside_printable_area_on_a_page(
    client_request,
    fake_uuid,
    invalid_pages,
    page_requested,
    overlay_expected,
    mocker,
):
    # Moved here from tests/app/main/views/uploads/test_upload_letter.py: this test exercises
    # app.main.views_nl.uploads (the only registered "upload a letter" blueprint), and its
    # letter_address_placement="60mm" assertion is NL-specific (the field doesn't exist
    # upstream) - see .claude/rules/tests.md.
    mocker.patch(
        "app.main.views_nl.uploads.get_letter_pdf_and_metadata",
        return_value=(
            "pdf_file",
            {
                "message": "content-outside-printable-area",
                "invalid_pages": invalid_pages,
            },
        ),
    )
    template_preview_mock_valid = mocker.patch(
        "app.template_preview_client.get_png_for_valid_pdf_page",
        return_value=make_response("page.html", 200),
    )
    template_preview_mock_invalid = mocker.patch(
        "app.template_preview_client.get_png_for_invalid_pdf_page",
        return_value=make_response("page.html", 200),
    )

    client_request.get_response(
        "main.view_letter_upload_as_preview",
        file_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        page=page_requested,
    )

    if overlay_expected:
        template_preview_mock_invalid.assert_called_once_with(
            "pdf_file", page_requested, letter_address_placement="60mm"
        )
        assert template_preview_mock_valid.called is False
    else:
        template_preview_mock_valid.assert_called_once_with("pdf_file", page_requested)
        assert template_preview_mock_invalid.called is False
