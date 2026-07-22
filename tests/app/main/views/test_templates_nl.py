import uuid
from unittest.mock import Mock

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from tests import sample_uuid
from tests.conftest import (
    SERVICE_ONE_ID,
    create_template,
    normalize_spaces,
)


def test_edit_letter_templates_postage_updates_postage(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    mock_get_service_letter_template,
):
    mock_update_template_postage = mocker.patch(
        "app.main.views_nl.templates.service_api_client.update_service_template"
    )

    client_request.post(
        "main.edit_template_postage",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"postage": "netherlands"},
    )
    mock_update_template_postage.assert_called_with(SERVICE_ONE_ID, fake_uuid, postage="netherlands")


@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        "sms",
        "letter",
    ),
)
def test_add_service_template_should_include_save_and_preview_button(
    client_request,
    service_one,
    template_type,
):
    if template_type == "letter":
        service_one["permissions"].append("letter")

    page = client_request.get(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
    )
    assert "Opslaan en voorbeeld bekijken" in page.text


@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        "sms",
        "letter",
    ),
)
def test_edit_service_template_should_include_save_and_preview_button(
    client_request, template_type, mock_get_service_letter_template, fake_uuid, service_one
):
    service_one["permissions"].append("letter")
    page = client_request.get(".edit_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid)

    assert "Opslaan en voorbeeld bekijken" in page.text


@pytest.mark.parametrize(
    "old_content, new_content, extra_email_file, expected_paragraphs, expected_placeholders",
    [
        # remove an email file placeholder
        (
            "here is your invite: ((invite.pdf))",
            "We will send your invite separately.",
            [],
            [
                "U hebt verwijderd de bestand ((invite.pdf)).",
                "Weet u zeker dat u deze bestand wilt verwijderen?",
            ],
            ["((invite.pdf))"],
        ),
        # remove an email file placeholder and remove a regular placeholder
        (
            "Dear ((name)), here is your invite: ((invite.pdf))",
            "We will send your invite separately.",
            [],
            [
                "U hebt verwijderd de bestand ((invite.pdf)).",
                "Weet u zeker dat u deze bestand wilt verwijderen?",
            ],
            ["((invite.pdf))"],
        ),
        # remove an email file placeholder and add a regular placeholder
        (
            "Dear ((name)), here is your invite: ((invite.pdf))",
            "((greeting)), We will send your invite separately.",
            [],
            [
                "U hebt verwijderd de bestand ((invite.pdf)).",
                "U hebt verwijderd de placeholder ((name)).",
                "U hebt toegevoegd de placeholder ((greeting)).",
                (
                    "Bevestig dat u: "
                    "dit bestand wilt verwijderen. "
                    "eventuele API-aanroepen voor dit sjabloon zult aanpassen zodat deze greeting "
                    "bevatten voordat u berichten verstuurt."
                ),
            ],
            ["((invite.pdf))", "((name))", "((greeting))"],
        ),
        # remove two email files, remove a regular placeholder and add two regular placeholders
        (
            "Dear ((name)), here is your invite: ((invite.pdf)) and map: ((map.jpeg))",
            "((greeting)), We will send your invite separately. ((footer))",
            [
                {
                    "id": str(uuid.UUID(int=1, version=4)),
                    "filename": "map.jpeg",
                    "link_text": None,
                    "retention_period": 90,
                    "validate_users_email": False,
                }
            ],
            [
                "U hebt verwijderd de bestands:",
                "U hebt verwijderd de placeholder ((name)).",
                "U hebt toegevoegd de placeholders:",
                (
                    "Bevestig dat u: "
                    "deze bestanden wilt verwijderen. "
                    "eventuele API-aanroepen voor dit sjabloon zult aanpassen zodat deze greeting en footer"
                    " bevatten voordat u berichten verstuurt."
                ),
            ],
            ["((invite.pdf))", "((map.jpeg))", "((name))", "((greeting))", "((footer))"],
        ),
    ],
)
def test_edit_service_template_asks_confirmation_when_removing_email_files(
    client_request,
    service_one,
    mock_get_api_keys,
    fake_uuid,
    mocker,
    old_content,
    new_content,
    extra_email_file,
    expected_paragraphs,
    expected_placeholders,
):
    service_one["permissions"] += ["email"]

    # mock out template with email files
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        subject="Your ((thing)) is due soon",
        content=old_content,
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ]
        + extra_email_file,
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})

    edit_request_data = {
        "id": fake_uuid,
        "template_content": new_content,
        "template_type": "email",
        "subject": "reminder '\" <span> & ((thing))",
        "service": SERVICE_ONE_ID,
    }

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data=edit_request_data,
        _expected_status=200,
    )

    assert page.select_one("h1").string.strip() == "Wijzigingen bevestigen"
    assert page.select_one("a.govuk-back-link")["href"] == url_for(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [normalize_spaces(paragraph.text) for paragraph in page.select("main p")] == expected_paragraphs

    assert [
        normalize_spaces(placeholder.text) for placeholder in page.select("span.placeholder")
    ] == expected_placeholders


def test_should_not_edit_letter_template_with_too_big_qr_code(
    client_request,
    mock_get_service_template,
    mock_update_service_template_400_qr_code_too_big,
    mock_get_no_api_keys,
    fake_uuid,
    service_one,
):
    service_one["permissions"].append("letter")

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "name": "new name",
            "subject": "subject",
            "template_content": "qr: " + ("content" * 100),
            "template_type": "letter",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == (
        "Er is een probleem Cannot create a usable QR code - the link you entered is too long"
    )
    # The "Error:" visually-hidden prefix comes from the vendored (untranslated)
    # govuk_frontend_jinja error-message macro's default, so it stays in English.
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Error: Cannot create a usable QR code - the link you entered is too long"
    )


def test_attach_files_button_letter_translation(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_page_counts_for_letter,
    single_letter_contact_block,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="letter",
                email_files=None,
            )
        },
    )
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    button = page.select_one(".js-stick-at-bottom-when-scrolling .govuk-button--secondary")

    assert button["href"] == url_for(
        "main.letter_template_attach_pages", service_id=SERVICE_ONE_ID, template_id=fake_uuid
    )
    assert normalize_spaces(button.text) == "Pagina’s bijvoegen"


def test_should_show_delete_template_page_with_time_block(
    client_request, mock_get_service_template, mock_get_template_folders, mocker, fake_uuid
):
    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value="2012-01-01 12:00:00")

    with freeze_time("2012-01-01 12:10:00"):
        page = client_request.get(
            ".delete_service_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _test_page_title=False,
        )
    assert "Weet u zeker dat u ‘Two week reminder’ wilt verwijderen?" in page.select(".banner-dangerous")[0].text
    assert normalize_spaces(page.select(".banner-dangerous p")[0].text) == (
        "Dit sjabloon is voor het laatst gebruikt 10 minuten geleden."
    )
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == (
        "service one: Template <em>content</em> with & entity"
    )
    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_should_show_delete_template_page_with_time_block_for_empty_notification(
    client_request, mock_get_service_template, mock_get_template_folders, mocker, fake_uuid
):
    mocker.patch("app.template_statistics_client.get_last_used_date_for_template", return_value=None)

    with freeze_time("2012-01-01 11:00:00"):
        page = client_request.get(
            ".delete_service_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _test_page_title=False,
        )

    expected_confirmation_question = "Weet u zeker dat u ‘Two week reminder’ wilt verwijderen?"
    expected_usage_hint = "Dit sjabloon is het afgelopen jaar niet gebruikt."
    expected_template_content = "service one: Template <em>content</em> with & entity"

    assert expected_confirmation_question in page.select(".banner-dangerous")[0].text
    assert normalize_spaces(page.select(".banner-dangerous p")[0].text) == expected_usage_hint
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == expected_template_content

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_should_show_delete_template_page_with_never_used_block(
    client_request,
    mock_get_service_template,
    mock_get_template_folders,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.template_statistics_client.get_last_used_date_for_template",
        side_effect=HTTPError(response=Mock(status_code=404), message="Default message"),
    )
    page = client_request.get(
        ".delete_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert "Weet u zeker dat u ‘Two week reminder’ wilt verwijderen?" in page.select(".banner-dangerous")[0].text
    assert not page.select(".banner-dangerous p")
    assert normalize_spaces(page.select(".sms-message-wrapper")[0].text) == (
        "service one: Template <em>content</em> with & entity"
    )
    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, fake_uuid, None)


def test_get_delete_letter_attachment_shows_confirmation(
    mock_get_service_letter_template_with_attachment,
    client_request,
    service_one,
    mocker,
):
    mock_flash = mocker.patch("app.main.views_nl.templates.flash")
    mocker.patch("app.letter_attachment_client.archive_letter_attachment")
    page = client_request.get(
        "main.letter_template_edit_pages",
        service_id=SERVICE_ONE_ID,
        template_id=sample_uuid(),
        _expected_status=200,
    )
    mock_flash.assert_called_once_with("Weet u zeker dat u de bijlage ‘original file.pdf’ wilt verwijderen?", "remove")
    assert page.select_one("h1").text.strip() == "original file.pdf"


def test_should_show_redact_template(
    client_request,
    mock_get_service_template,
    mock_redact_template,
    service_one,
    fake_uuid,
):
    page = client_request.post(
        "main.redact_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == (
        "Gepersonaliseerde inhoud wordt verborgen voor berichten die met dit sjabloon worden verzonden"
    )

    mock_redact_template.assert_called_once_with(SERVICE_ONE_ID, fake_uuid)


@pytest.mark.parametrize(
    "new_content, expected_file_ids_to_archive, expected_banner_text",
    (
        (
            "For the appointment, you will just need ((map.pdf))",
            [
                "00000000-0000-4000-8000-000000000001",
                "00000000-0000-4000-8000-000000000002",
            ],
            "‘invite.pdf’ en ‘form.pdf’ zijn verwijderd",
        ),
        (
            "For the appointment, you will just need ((form.pdf)) and ((map.pdf))",
            [
                "00000000-0000-4000-8000-000000000001",
            ],
            "‘invite.pdf’ is verwijderd",
        ),
    ),
)
def test_edit_service_template_archives_email_files(
    client_request,
    fake_uuid,
    mocker,
    new_content,
    expected_file_ids_to_archive,
    expected_banner_text,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        subject="Your ((thing)) is due soon",
        content="For the appointment, you will need: ((invite.pdf)), ((form.pdf)), ((map.pdf))",
        email_files=[
            {
                "id": str(uuid.UUID(int=1, version=4)),
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
            {
                "id": str(uuid.UUID(int=2, version=4)),
                "filename": "form.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
            {
                "id": str(uuid.UUID(int=3, version=4)),
                "filename": "map.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})

    mock_update_service_template = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "template_content": new_content,
            "template_type": "email",
            "service": SERVICE_ONE_ID,
            "confirm": True,
        },
        _follow_redirects=True,
    )
    mock_update_service_template.assert_called_with(
        "POST",
        "/service/596364a0-858e-42c8-9062-a8fe822260eb/template/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6",
        data={
            "created_by": "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6",
            "content": new_content,
            "subject": "Your ((thing)) is due soon",
            "name": "sample template",
            "has_unsubscribe_link": False,
            "archive_email_file_ids": expected_file_ids_to_archive,
        },
    )

    assert normalize_spaces(page.select(".banner-default-with-tick")[0].text) == expected_banner_text
