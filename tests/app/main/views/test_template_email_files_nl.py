import uuid
from io import BytesIO
from unittest.mock import call

import pytest
from flask import url_for
from notifications_utils.testing.comparisons import AnyInstanceOf
from werkzeug.datastructures import FileStorage

from tests.conftest import SERVICE_ONE_ID, create_template, normalize_spaces, sample_uuid


@pytest.mark.parametrize(
    "template_content, expected_filenames_on_page",
    [
        (
            # No template content
            "",
            ["test_file_1.csv", "test_file_2.png"],
        ),
        (
            # Content order matches database order
            "((test_file_1.csv)) ((test_file_2.png))",
            ["test_file_1.csv", "test_file_2.png"],
        ),
        (
            # Content order does not match database order
            "((test_file_2.png)) ((test_file_1.csv))",
            ["test_file_2.png", "test_file_1.csv"],
        ),
        (
            # Content order does not match database order (case differs)
            "((TEST FILE 2.PNG)) ((TEST FILE 1.CSV))",
            ["test_file_2.png", "test_file_1.csv"],
        ),
        (
            # Content order does not match database order (extra, non-file placeholders)
            "((test_file_2.png)) ((first name)) ((last name)) ((test_file_1.csv))",
            ["test_file_2.png", "test_file_1.csv"],
        ),
    ],
)
def test_template_email_files_manage_files_page_displays_the_right_files_in_the_right_order(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
    template_content,
    expected_filenames_on_page,
):
    service_one["contact_link"] = "https://example.gov.uk"
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
                content=template_content,
            )
        },
    )
    page = client_request.get(
        "main.template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select_one("h1").string.strip() == "Bestanden beheren"
    assert [normalize_spaces(row.text) for row in page.select("dt")] == expected_filenames_on_page

    assert (
        normalize_spaces(page.select_one('a[role="button"][data-module="govuk-button"]').get_text())
        == "Nog een bestand bijvoegen"
    )


def test_manage_a_template_email_file(
    service_one,
    fake_uuid,
    client_request,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    page = client_request.get(
        "main.manage_a_template_email_file",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_data_for_a_template_email_file["id"],
    )

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.template_email_files", service_id=SERVICE_ONE_ID, template_id=fake_uuid
    )

    assert page.select_one("h1").string.strip() == test_data_for_a_template_email_file["filename"]

    rows = page.select("dl .govuk-summary-list__row:not(.govuk-visually-hidden)")
    assert [normalize_spaces(row.get_text(separator=" ", strip=True)) for row in rows] == [
        "Linktekst Niet ingesteld Wijzigen linktekst voor het bestand",
        (
            "Beschikbaar voor 90 weken na verzenden (ongeveer 1 jaar, 9 maanden) "
            "Wijzigen hoe lang het bestand beschikbaar is nadat het is verstuurd"
        ),
        "Vraag ontvanger om e-mailadres Nee Wijzigen of de ontvanger om een e-mailadres moet worden gevraagd",
    ]
    delete_link = page.select_one("a.govuk-link.govuk-link--destructive")
    assert normalize_spaces(delete_link) == "Dit bestand verwijderen"
    assert (
        delete_link["href"]
        == f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{test_data_for_a_template_email_file['id']}?delete=true"  # noqa: E501
    )
    assert not page.select_one("div.banner-dangerous")
    page = client_request.get(
        "main.manage_a_template_email_file",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_data_for_a_template_email_file["id"],
        delete=True,
    )
    banner = page.select_one("div.banner-dangerous")
    assert (normalize_spaces(banner)) == "Weet u zeker dat u dit bestand wilt verwijderen? Ja, verwijderen"
    assert (
        banner.select_one("form")["action"]
        == f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{test_data_for_a_template_email_file['id']}?delete=true"  # noqa: E501
    )
    assert banner.select_one("form")["method"] == "post"


def test_post_delete_to_manage_a_template_email_file_updates_and_redirects(
    service_one,
    fake_uuid,
    client_request,
    test_template_email_files_data,
    test_data_for_a_template_email_file,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
                content="This template contains an email file ((test_file_1.csv))",
            )
        },
    )
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    mock_update_service_template = mocker.patch(
        "app.notify_client.service_api_client.ServiceAPIClient.update_service_template"
    )
    page = client_request.post(
        "main.manage_a_template_email_file",
        service_id=service_one["id"],
        template_id=fake_uuid,
        template_email_file_id=test_data_for_a_template_email_file["id"],
        delete=True,
        _follow_redirects=True,
    )
    mock_update_service_template.assert_called_once_with(
        service_id=service_one["id"],
        template_id=fake_uuid,
        content="This template contains an email file",
        archive_email_file_ids=[test_data_for_a_template_email_file["id"]],
    )
    assert normalize_spaces(page.select_one("h1.folder-heading")) == "sample template"
    assert normalize_spaces(page.select_one(".banner-default-with-tick")) == "‘test_file_1.csv’ is verwijderd"


@pytest.mark.parametrize(
    "endpoint, page_title, form_label, path_segment",
    [
        (
            "main.change_link_text",
            "Linktekst toevoegen",
            "Linktekst (optioneel)",
            "change-link-text",
        ),
        (
            "main.change_data_retention_period",
            "Hoe lang het bestand beschikbaar is",
            "Aantal weken beschikbaar voor ontvangers",
            "change-data-retention",
        ),
    ],
)
def test_file_settings_pages_for_link_text_and_retention_period(
    client_request,
    service_one,
    fake_uuid,
    endpoint,
    page_title,
    form_label,
    test_template_email_files_data,
    path_segment,
    mocker,
):
    template_id = fake_uuid
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=template_id,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    template_email_file_id = test_template_email_files_data[0]["id"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        template_email_file_id=template_email_file_id,
    )
    assert page.select_one("h1").string.strip() == page_title
    assert page.select_one("label").string.strip() == form_label
    form = page.select_one("form[method='post']")
    button = form.select_one(".govuk-button")
    expected_url = f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{template_email_file_id}/{path_segment}"
    assert button.text.strip() == "Doorgaan"
    assert form["action"] == expected_url


def test_file_settings_pages_for_email_validation(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
):
    template_id = fake_uuid
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=template_id,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    template_email_file_id = test_template_email_files_data[0]["id"]
    page = client_request.get(
        "main.change_email_validation",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        template_email_file_id=template_email_file_id,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Vraag de ontvanger om zijn/haar e-mailadres"
    assert normalize_spaces(page.select_one("h1 + p").text) == (
        "De ontvanger moet zijn/haar e-mailadres invoeren voordat hij/zij ‘test_file_1.csv’ kan downloaden."
    )
    assert normalize_spaces(page.select_one("legend").text) == (
        "Wilt u dat de ontvanger zijn/haar e-mailadres bevestigt?"
    )
    assert [normalize_spaces(label.text) for label in page.select(".govuk-radios__item label")] == [
        "Ja",
        "Nee",
    ]

    form = page.select_one("form[method='post']")
    button = form.select_one(".govuk-button")
    expected_url = (
        f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{template_email_file_id}/change-email-validation"
    )
    assert normalize_spaces(button.text) == "Doorgaan"
    assert form["action"] == expected_url


@pytest.mark.parametrize(
    "retention_period, expected_error_message",
    (
        ("", "Vul een aantal weken in"),
        ("hello", "Voer het aantal weken in getallen in"),
        ("0", "Vul een aantal weken in"),
        ("79", "Het aantal weken moet tussen 1 en 78 liggen"),
    ),
)
def test_validate_retention_period(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    retention_period,
    expected_error_message,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    test_template_email_files_data[0]["template_id"] = fake_uuid
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    page = client_request.post(
        "main.change_data_retention_period",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_template_email_files_data[0]["id"],
        _data={"retention_period": retention_period},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == (
        f"Er is een probleem {expected_error_message}"
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == f"Error: {expected_error_message}"


def test_create_file_redirects_to_manage_files_page(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
    active_user_with_permissions,
    mock_update_service,
    mock_get_service_email_template,
):
    service_one["contact_link"] = "htttps://example.gov.uk"
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = ["view_activity", "manage_templates"]
    client_request.login(active_user_with_permissions)
    file_id = uuid.uuid4()
    mock_create_file = mocker.patch("app.models.template_email_file.TemplateEmailFile.create", return_value=file_id)
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={
            "data": {
                "filename": "tests/test_pdf_files/one_page_pdf.pdf",
                "id": str(file_id),
                "link_text": None,
                "retention_period": 78,
                "validate_users_email": False,
                "pending": True,
            }
        },
    )
    mocker.patch(
        "app.extensions.antivirus_client.scan",
        return_value=True,
    )
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.upload_template_email_files",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _follow_redirects=True,
        )
    assert mock_create_file.call_args_list == [
        call(
            filename="tests/test_pdf_files/one_page_pdf.pdf",
            file_contents=AnyInstanceOf(FileStorage),
            template_id=fake_uuid,
        ),
    ]
    assert normalize_spaces(page.select_one("form .govuk-button")) == "Toevoegen aan sjabloon"
    assert page.select_one("form").get("method") == "post"
    assert (
        page.select_one("form").get("action")
        == f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}/files/{file_id}/make-live"
    )


@pytest.mark.parametrize(
    "template_content, expected_calls",
    (
        (
            "Template content",
            [
                call(
                    template_id=sample_uuid(),
                    service_id=SERVICE_ONE_ID,
                    content="Template content\n\n((test_file_1.csv))",
                )
            ],
        ),
        ("Already has placeholder ((test_file_1.csv))", []),
        ("Already has placeholder in different case/whitespace ((TEST FILE 1.csv))", []),
    ),
)
def test_make_live_endpoint_calls_update_with_correct_args(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
    active_user_with_permissions,
    mock_update_service,
    mock_get_service_email_template,
    template_content,
    expected_calls,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                content=template_content,
            )
        },
    )
    file_data = {
        "filename": "test_file_1.csv",
        "id": "e9ecb3f2-8674-4436-b233-d2c16ad135e7",
        "link_text": None,
        "retention_period": 90,
        "validate_users_email": False,
        "pending": True,
        "template_id": fake_uuid,
    }
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": file_data},
    )
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    mock_template_email_file_update = mocker.patch("app.models.template_email_file.TemplateEmailFile.update")
    page = client_request.post(
        "main.make_file_live",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=file_data["id"],
        _follow_redirects=True,
    )
    assert mock_template_update.call_args_list == expected_calls
    assert mock_template_email_file_update.call_args_list == [call(pending=False)]
    assert normalize_spaces(page.select_one("h1.folder-heading")) == "sample template"
    assert normalize_spaces(page.select_one(".banner-default-with-tick")) == "‘test_file_1.csv’ toegevoegd aan sjabloon"


@pytest.mark.parametrize("pending", [True, False])
def test_change_retention_period_page(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
    pending,
):
    test_template_email_files_data[0]["pending"] = pending
    test_template_email_files_data[1]["pending"] = pending
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    test_template_email_files_data[0]["template_id"] = fake_uuid
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )

    page = client_request.get(
        "main.change_data_retention_period",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_template_email_files_data[0]["id"],
    )
    assert page.select_one("h1").string.strip() == "Hoe lang het bestand beschikbaar is"
    assert normalize_spaces(page.select_one("p")) == ("Kies hoe lang ontvangers toegang hebben tot ‘test_file_1.csv’.")
    assert page.select_one("label").string.strip() == "Aantal weken beschikbaar voor ontvangers"
    assert page.select_one("button[type=submit]").string.strip() == "Doorgaan"


def test_setup_template_email_files_page(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
):
    page = client_request.get(
        "main.setup_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Bestanden per e-mail verzenden"
    # Note that the rest of the tests for the form are in test_service_settings.py
    assert page.select_one("main form")
    assert [normalize_spaces(p.text) for p in page.select("main p.govuk-body")] == [
        "Upload een bestand en stuur uw ontvangers een e-mail met een link om het te downloaden.",
        "U moet contactgegevens voor uw dienst toevoegen zodat uw gebruikers contact kunnen opnemen bij problemen. "
        "Bijvoorbeeld wanneer de link om het bestand te downloaden is verlopen.",
    ]


def test_setup_template_email_files_page_without_manage_service_permission(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    active_user_with_permissions,
    mock_update_service,
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = ["view_activity", "manage_templates"]
    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.setup_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Bestanden per e-mail verzenden"
    assert not page.select_one("main form")
    assert [normalize_spaces(p.text) for p in page.select("main p.govuk-body")] == [
        "Upload een bestand en stuur uw ontvangers een e-mail met een link om het te downloaden.",
        "U moet contactgegevens voor uw dienst toevoegen zodat uw gebruikers contact kunnen opnemen bij problemen. "
        "Bijvoorbeeld wanneer de link om het bestand te downloaden is verlopen.",
        "Vraag een teamlid met de rechten ‘Instellingen, team en gebruik beheren’ om dit voor u in te stellen.",
    ]

    client_request.post(
        "main.setup_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "contact_details_type": "url",
            "url": "http://example.com",
        },
        _expected_status=200,
    )
    assert mock_update_service.call_args_list == []


@pytest.mark.parametrize(
    "template_type, contact_link, expected_status",
    (
        # With different template types
        (
            "email",
            "http://example.com",
            200,
        ),
    ),
)
def test_get_upload_file_page(
    client_request,
    service_one,
    fake_uuid,
    template_type,
    contact_link,
    expected_status,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type=template_type,
            )
        },
    )
    service_one["contact_link"] = contact_link
    page = client_request.get(
        "main.upload_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=expected_status,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Bestand toevoegen"

    file_upload_field = page.select_one("form[data-notify-module=file-upload] input[type=file]")
    assert file_upload_field["accept"] == (".csv,.jpeg,.jpg,.png,.xlsx,.doc,.docx,.pdf,.json,.odt,.rtf,.txt")
    assert file_upload_field["data-button-text"] == "Bestand kiezen"

    assert [normalize_spaces(li.text) for li in page.select("main ul li")] == [
        "CSV (.csv)",
        "image (.jpeg, .jpg, .png)",
        "Microsoft Excel Spreadsheet (.xlsx)",
        "Microsoft Word Document (.doc, .docx)",
        "PDF (.pdf)",
        "text (.json, .odt, .rtf, .txt)",
    ]


def test_upload_file_page_requires_file(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_email_template,
):
    service_one["contact_link"] = "https://example.com"
    page = client_request.post(
        "main.upload_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-summary")) == (
        "Er is een probleem U moet een bestand uploaden om te versturen"
    )
    assert (
        normalize_spaces(page.select_one("form label .govuk-error-message"))
        == "U moet een bestand uploaden om te versturen"
    )


@pytest.mark.parametrize(
    "test_file, expected_error_message",
    (
        (
            "tests/spreadsheet_files/equivalents/EXCEL_95.XLS",
            ".XLS is geen toegestaan bestandsformaat",
        ),
        (
            "tests/test_pdf_files/big.pdf",
            "Het bestand moet kleiner zijn dan 2MB",
        ),
        (
            "tests/text_files/with (brackets).txt",
            "Bestandsnaam mag geen haakjes bevatten",
        ),
        (
            "tests/text_files/no extension",
            "Geen toegestaan bestandsformaat",
        ),
    ),
)
def test_upload_file_page_validates_extentions(
    client_request,
    fake_uuid,
    service_one,
    mock_get_service_email_template,
    test_file,
    expected_error_message,
    mocker,
):
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mocker.patch("app.template_email_file_client.post")
    mocker.patch("app.service_api_client.update_service_template")
    service_one["contact_link"] = "https://example.com"
    with open(test_file, "rb") as file:
        page = client_request.post(
            "main.upload_template_email_files",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=200,  # if the form fails to validate we should return upload view with msg
        )

    assert mock_antivirus.called
    error_message = page.select_one("form label .govuk-error-message")
    assert normalize_spaces(error_message.text) == expected_error_message


@pytest.mark.parametrize(
    "filename, expected_length, expected_status, expected_file_created",
    (
        pytest.param(
            ("a" * 97) + ".pdf",
            101,
            200,
            False,
        ),
    ),
)
def test_upload_file_returns_error_if_filename_is_too_long(
    client_request,
    fake_uuid,
    service_one,
    mocker,
    mock_get_service_email_template,
    filename,
    expected_status,
    expected_length,
    expected_file_created,
):
    assert len(filename) == expected_length
    service_one["contact_link"] = "https://example.com"
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")

    page = client_request.post(
        "main.upload_template_email_files",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"file": (BytesIO(b"abcdef"), filename)},
        _expected_status=expected_status,
    )

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Bestandsnaam mag niet langer zijn dan 100 tekens (‘"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf’ "
        "is 101 tekens)"
    )

    assert mock_antivirus.called is True
    assert mock_s3.called is expected_file_created
    assert mock_post.called is expected_file_created


@pytest.mark.parametrize(
    "existing_filename",
    (
        ("tests/test_pdf_files/one_page_pdf.pdf"),
        ("tests/test_pdf_files/ONE-PAGE PDF.PDF"),
    ),
)
def test_upload_file_returns_error_if_file_with_same_name_exists(
    client_request,
    fake_uuid,
    service_one,
    mocker,
    existing_filename,
):
    service_one["contact_link"] = "https://example.com"
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=[
                    {
                        "id": fake_uuid,
                        "filename": existing_filename,
                        "link_text": None,
                        "retention_period": 90,
                        "validate_users_email": False,
                    },
                ],
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.upload_template_email_files",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=200,
        )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Uw sjabloon heeft al een bestand met de naam ‘tests/test_pdf_files/one_page_pdf.pdf’"
    )
    assert mock_antivirus.called is True
    assert mock_template_update.call_args_list == []
    assert mock_s3.call_args_list == []
    assert mock_post.call_args_list == []


@pytest.mark.parametrize(
    "subject",
    (
        ("Please download ((tests/test_pdf_files/one_page_pdf.pdf))"),
        ("Please download ((tests/test_pdf_files/ONE-PAGE PDF.PDF))"),
    ),
)
def test_upload_file_returns_error_if_placeholder_exists_in_subject(
    client_request,
    fake_uuid,
    service_one,
    mocker,
    subject,
):
    service_one["contact_link"] = "https://example.com"
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                subject=subject,
            )
        },
    )
    mock_antivirus = mocker.patch("app.extensions.antivirus_client.scan", return_value=True)
    mock_s3 = mocker.patch("app.s3_client.s3_template_email_file_upload_client.utils_s3upload")
    mock_post = mocker.patch("app.template_email_file_client.post")
    mock_template_update = mocker.patch("app.service_api_client.update_service_template")
    with open("tests/test_pdf_files/one_page_pdf.pdf", "rb") as file:
        page = client_request.post(
            "main.upload_template_email_files",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _data={"file": file},
            _expected_status=200,
        )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "U kunt geen bestand in het onderwerp van een sjabloon plaatsen – "
        "verwijder ((tests/test_pdf_files/one_page_pdf.pdf)) of hernoem uw bestand"
    )
    assert mock_antivirus.called is True
    assert mock_template_update.call_args_list == []
    assert mock_s3.call_args_list == []
    assert mock_post.call_args_list == []


def test_change_email_validation_page_has_backlink_and_form_action(
    client_request,
    service_one,
    fake_uuid,
    test_template_email_files_data,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": create_template(
                template_id=fake_uuid,
                template_type="email",
                email_files=test_template_email_files_data,
            )
        },
    )
    mocker.patch(
        "app.notify_client.template_email_file_client.TemplateEmailFileClient.get_file_by_id",
        return_value={"data": test_template_email_files_data[0]},
    )
    page = client_request.get(
        "main.change_link_text",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        template_email_file_id=test_template_email_files_data[0]["id"],
    )
    assert page.select_one(".govuk-back-link").text.strip() == "Terug"
