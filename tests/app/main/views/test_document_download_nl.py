from unittest.mock import PropertyMock

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_utils.base64_uuid import uuid_to_base64

from tests import service_json
from tests.conftest import SERVICE_ONE_ID, create_template, normalize_spaces


@pytest.mark.parametrize(
    "contact_link_value, expected_paragraphs, expected_link_text, expected_url",
    (
        (
            None,
            [
                "Test Service heeft u een bestand gestuurd om te downloaden.",
                "Doorgaan",
            ],
            None,
            None,
        ),
        (
            "http://example.com/",
            [
                "Test Service heeft u een bestand gestuurd om te downloaden.",
                "Doorgaan",
                "Heeft u vragen? Neem contact op met Test Service.",
            ],
            "Neem contact op met Test Service",
            "http://example.com/",
        ),
        (
            "me@example.com",
            [
                "Test Service heeft u een bestand gestuurd om te downloaden.",
                "Doorgaan",
                "Heeft u vragen? Mail naar me@example.com.",
            ],
            "me@example.com",
            "mailto:me@example.com",
        ),
        (
            "0207 123 4567",
            [
                "Test Service heeft u een bestand gestuurd om te downloaden.",
                "Doorgaan",
                "Heeft u vragen? Bel 0207 123 4567.",
            ],
            None,
            None,
        ),
    ),
)
def test_landing_page(
    client_request,
    fake_uuid,
    contact_link_value,
    expected_paragraphs,
    expected_link_text,
    expected_url,
    mocker,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": False,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    mocker.patch(
        "app.service_api_client.get_service",
        return_value={"data": service_json(SERVICE_ONE_ID, contact_link=contact_link_value)},
    )
    page = client_request.get(
        ".document_download_landing",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert normalize_spaces(page.select_one("main h1")) == "U heeft een bestand om te downloaden"
    assert [
        normalize_spaces(p.text) for p in page.select(".govuk-grid-column-two-thirds > p.govuk-body")
    ] == expected_paragraphs

    button = page.select_one("a.govuk-button")
    assert button["href"] == url_for(
        "main.document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert normalize_spaces(button.text) == "Doorgaan"

    link = page.select_one(".govuk-grid-column-two-thirds > p.govuk-body a.govuk-link")
    assert not expected_url or link["href"] == expected_url
    assert normalize_spaces(link) == expected_link_text


@pytest.mark.parametrize(
    "contact_link_value, expected_paragraphs, expected_link_text, expected_url",
    (
        (
            None,
            [
                "Om veiligheidsredenen moeten we bevestigen naar welk e-mailadres het bestand is gestuurd "
                "voordat u het kunt downloaden.",
            ],
            None,
            None,
        ),
        (
            "http://example.com/",
            [
                "Om veiligheidsredenen moeten we bevestigen naar welk e-mailadres het bestand is gestuurd "
                "voordat u het kunt downloaden.",
                "Heeft u vragen? Neem contact op met Test Service.",
            ],
            "Neem contact op met Test Service",
            "http://example.com/",
        ),
        (
            "me@example.com",
            [
                "Om veiligheidsredenen moeten we bevestigen naar welk e-mailadres het bestand is gestuurd "
                "voordat u het kunt downloaden.",
                "Heeft u vragen? Mail naar me@example.com.",
            ],
            "me@example.com",
            "mailto:me@example.com",
        ),
        (
            "0207 123 4567",
            [
                "Om veiligheidsredenen moeten we bevestigen naar welk e-mailadres het bestand is gestuurd "
                "voordat u het kunt downloaden.",
                "Heeft u vragen? Bel 0207 123 4567.",
            ],
            None,
            None,
        ),
    ),
)
def test_confirm_email_page_shows_form_if_confirmation_required(
    client_request,
    fake_uuid,
    mocker,
    contact_link_value,
    expected_paragraphs,
    expected_link_text,
    expected_url,
):
    mocker.patch(
        "app.service_api_client.get_service",
        return_value={"data": service_json(SERVICE_ONE_ID, contact_link=contact_link_value)},
    )
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    page = client_request.get(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )

    assert normalize_spaces(page.select_one("h1").text) == "Bevestig uw e-mailadres"

    form = page.select_one("form")
    assert form["action"] == url_for(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    assert form["autocomplete"] == "off"
    assert form["novalidate"] == ""
    assert form["method"] == "post"
    assert normalize_spaces(form.select_one("label[for=email_address]").text) == "E-mailadres"
    assert "value" not in form.select_one("input[type=email][name=email_address]")
    assert normalize_spaces(form.select_one("button.govuk-button").text) == "Doorgaan"

    assert [
        normalize_spaces(p.text) for p in page.select(".govuk-grid-column-two-thirds > p.govuk-body")
    ] == expected_paragraphs

    link = page.select_one(".govuk-grid-column-two-thirds > p.govuk-body a.govuk-link")
    assert not expected_url or link["href"] == expected_url
    assert normalize_spaces(link) == expected_link_text


@pytest.mark.parametrize(
    "email_address, expected_error",
    (
        ("", "Vul e-mailadres in"),
        ("testing", "Geen geldig e-mailadres"),
        (
            "not-current-user@example.gov.uk",
            (
                "Dit is niet het e-mailadres waar het bestand naartoe is gestuurd."
                "Voer het e-mailadres in waar Test Service het bestand naartoe heeft gestuurd "
                "om te bevestigen dat het bestand voor u bedoeld was."
            ),
        ),
    ),
)
def test_confirm_email_page_shows_errors(
    client_request,
    fake_uuid,
    mocker,
    email_address,
    expected_error,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    page = client_request.post(
        ".document_download_confirm_email_address",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
        _data={
            "email_address": email_address,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == f"Er is een probleem {expected_error}"
    # [NOTIFYNL] the visually-hidden "Error:" prefix stays English app-wide — see
    # "govukInput error-message untranslated 'Error:' prefix" in memory, out of scope here.
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == f"Error: {expected_error}"


@pytest.mark.parametrize(
    "endpoint, expected_banner_text",
    (
        (
            ".document_download_landing",
            (
                "Voorbeeld "
                "Dit is een voorbeeld van de pagina die uw ontvangers zullen zien "
                "Om het bestand te wijzigen of te verwijderen, bewerkt u het e-mailsjabloon."
            ),
        ),
        (
            ".document_download_confirm_email_address",
            (
                "Voorbeeld "
                "Dit is een voorbeeld van de pagina die uw ontvangers zullen zien "
                "Om het bestand te wijzigen of te verwijderen, bewerkt u het e-mailsjabloon. "
                "Voer om door te gaan het e-mailadres in waarmee u inlogt bij NotifyNL."
            ),
        ),
        (
            ".document_download_download_document",
            (
                "Voorbeeld "
                "Dit is een voorbeeld van de pagina die uw ontvangers zullen zien "
                "Om het bestand te wijzigen of te verwijderen, bewerkt u het e-mailsjabloon."
            ),
        ),
    ),
)
def test_banner_on_all_pages(
    client_request,
    fake_uuid,
    mocker,
    endpoint,
    expected_banner_text,
):
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": "invite.pdf",
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    mocker.patch(
        "app.models.template_email_file.TemplateEmailFile.size",
        new_callable=PropertyMock,
        return_value=123,
    )
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )
    banner = page.select_one(".govuk-notification-banner")
    assert normalize_spaces(banner.text) == expected_banner_text
    assert banner.select_one("a")["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "file_name, file_type, service_contact_link, file_content_length, expected_file_size, contact_content",
    [
        ("test_file_1.pdf", "PDF", "me@example.com", 15728640, "15MB", "Mail naar me@example.com"),
        ("test_file_2.csv", "CSV file", "https://example.com/", 51200, "5KB", "Neem contact op met Test Service"),
        ("test_file_3.png", "PNG file", "0207 123 4567", 1057000, "1MB", "Bel 0207 123 4567"),
        ("test_file_4.txt", "text file", "me@example.com", 102, "0.1KB", "Mail naar me@example.com"),
        ("test_file_5.png", "PNG file", "0207 123 4567", 10, "0.1KB", "Bel 0207 123 4567"),
        (
            "test_file_6.xlsx",
            "Microsoft Excel spreadsheet",
            "https://example.com/",
            56473898653,
            "53857.7MB",
            "Neem contact op met Test Service",
        ),
    ],
)
@freeze_time("2026-01-01")
def test_document_download_download_document_displays_the_right_file_metadata(
    client_request,
    fake_uuid,
    file_name,
    file_type,
    service_contact_link,
    file_content_length,
    expected_file_size,
    contact_content,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service",
        return_value={"data": service_json(SERVICE_ONE_ID, contact_link=service_contact_link)},
    )
    email_template = create_template(
        template_id=fake_uuid,
        template_type="email",
        email_files=[
            {
                "id": fake_uuid,
                "filename": file_name,
                "link_text": None,
                "retention_period": 90,
                "validate_users_email": True,
            },
        ],
    )
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": email_template})
    mocker.patch(
        "app.models.template_email_file.TemplateEmailFile.size",
        new_callable=PropertyMock,
        return_value=file_content_length,
    )
    page = client_request.get(
        ".document_download_download_document",
        service_id=SERVICE_ONE_ID,
        document_id=fake_uuid,
        key=uuid_to_base64(fake_uuid),
    )

    assert normalize_spaces(page.select_one("h1").text) == "Download uw bestand"

    assert [normalize_spaces(row.text) for row in page.select(".govuk-grid-column-two-thirds > p.govuk-body")] == [
        "Dit bestand is te downloaden tot 23 september 2027.",
        "Zorg ervoor dat u het bestand opslaat op een plek waar u het kunt terugvinden.",
        f"Download dit {file_type} ({expected_file_size}) naar uw apparaat",
        f"Heeft u vragen? {contact_content}.",
    ]
