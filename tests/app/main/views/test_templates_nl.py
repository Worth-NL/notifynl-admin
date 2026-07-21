import uuid

import pytest
from flask import url_for

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
                    "eventuele API-aanroepen voor dit sjabloon zult aanpassen zodat deze greeting and footer"
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
