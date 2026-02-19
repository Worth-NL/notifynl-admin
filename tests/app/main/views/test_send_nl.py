import uuid
from functools import partial
from glob import glob
from os import path

import pytest
from flask import url_for

from tests import (
    template_json,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    create_template,
    do_mock_get_page_counts_for_letter,
    normalize_spaces,
)

template_types = ["email", "sms"]

unchanging_fake_uuid = uuid.uuid4()

# The * ignores hidden files, eg .DS_Store
test_spreadsheet_files = glob(path.join("tests", "spreadsheet_files", "*"))
test_non_spreadsheet_files = glob(path.join("tests", "non_spreadsheet_files", "*"))


@pytest.mark.parametrize(
    "row_index, expected_status",
    [
        (0, 404),
        (1, 404),
        (2, 200),
        (3, 200),
        (4, 200),
        (5, 404),
    ],
)
def test_404_for_previewing_a_row_out_of_range(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    row_index,
    expected_status,
):
    with client_request.session_transaction() as session:
        session["file_uploads"] = {fake_uuid: {"template_id": fake_uuid}}

    mocker.patch(
        "app.main.views_nl.send.s3download",
        return_value="""
        telefoonnummer,name,col1,col2,col3
        07700900001, A,   foo,  foo,  foo
        07700900002, B,   foo,  foo,  foo
        07700900003, C,   foo,  foo,  foo
    """,
    )

    page = client_request.get(
        "main.check_messages",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        row_index=row_index,
        _expected_status=expected_status,
    )

    assert "kolomnamen" not in page.text


@pytest.mark.parametrize(
    "user, template_type, expected_link_text, expected_link_url",
    [
        (
            create_active_user_with_permissions(),
            "sms",
            "Zie mijn telefoonnummer",
            partial(url_for, "main.send_one_off_to_myself"),
        ),
        (
            create_active_user_with_permissions(),
            "email",
            "Zie mijn e-mailadres",
            partial(url_for, "main.send_one_off_to_myself"),
        ),
        (create_active_user_with_permissions(), "letter", None, None),
        (create_active_caseworking_user(), "sms", None, None),
    ],
)
def test_send_one_off_has_skip_link(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    multiple_sms_senders,
    multiple_reply_to_email_addresses,
    mocker,
    template_type,
    expected_link_text,
    expected_link_url,
    user,
):
    template_data = create_template(template_id=fake_uuid, template_type=template_type)
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template_data})
    do_mock_get_page_counts_for_letter(mocker, count=9)

    client_request.login(user)
    page = client_request.get(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
        _follow_redirects=True,
    )

    skip_links = page.select("form a")

    if expected_link_text and expected_link_url:
        assert skip_links[1].text.strip() == expected_link_text
        assert skip_links[1]["href"] == expected_link_url(
            service_id=service_one["id"],
            template_id=fake_uuid,
        )
    else:
        with pytest.raises(IndexError):
            skip_links[1]


@pytest.mark.parametrize(
    "step_index, prefilled, expected_field_label",
    [
        (
            0,
            {},
            "telefoonnummer",
        ),
        (
            1,
            {"telefoonnummer": "07900900123"},
            "one",
        ),
        (
            2,
            {"telefoonnummer": "07900900123", "one": "one"},
            "two",
        ),
    ],
)
def test_send_one_off_shows_placeholders_in_correct_order(
    client_request,
    fake_uuid,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    mock_get_service_template_with_multiple_placeholders,
    multiple_sms_senders,
    step_index,
    prefilled,
    expected_field_label,
):
    with client_request.session_transaction() as session:
        session["recipient"] = None
        session["placeholders"] = prefilled

    page = client_request.get(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=step_index,
    )

    assert normalize_spaces(page.select_one("label").text) == expected_field_label


def test_send_one_off_has_sticky_header_for_letter_on_non_address_placeholders(
    client_request,
    fake_uuid,
    mock_get_live_service,
    mocker,
):
    template_data = create_template(template_type="letter", content="((body))")
    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template_data})
    do_mock_get_page_counts_for_letter(mocker, count=9)

    with client_request.session_transaction() as session:
        session["recipient"] = ""
        session["placeholders"] = {
            "address line 1": "foo",
            "address line 2": "bar",
            "address line 3": "2552 HN Den Haag",
            "address line 4": "",
            "address line 5": "",
            "address line 6": "",
        }

    page = client_request.get(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=6,  # NL letter template has 6 placeholders – we’re at the end
        _follow_redirects=True,
    )
    assert page.select(".js-stick-at-top-when-scrolling")


@pytest.mark.parametrize(
    "template_type, content, recipient, placeholder_values, step_index, css_selector_for_content, expected_content",
    (
        (
            "letter",
            "((address_line_1)) ((POSTCODE)) ((address_line_3)) ((name))",
            None,
            {
                "addressline1": "1 Example Street",
                "addressline2": "1234 AB",
                "addressline3": "Den Haag",
                "addressline4": "",
                "addressline5": "",
                "addressline6": "Netherlands",
                "postcode": "1234 AB",
            },
            7,  # NL postal address can only have 6 lines  #TODO: Should we still accept POSTCODE as placeholder?
            ".letter + .govuk-visually-hidden p:last-child",
            "1 Example Street 1234 AB Den Haag ((name))",
        ),
    ),
)
def test_send_one_off_only_asks_for_recipient_once(
    client_request,
    fake_uuid,
    template_type,
    mock_template_preview,
    content,
    recipient,
    placeholder_values,
    step_index,
    css_selector_for_content,
    expected_content,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": template_json(
                service_id=SERVICE_ONE_ID,
                id_=fake_uuid,
                name="Two week reminder",
                type_=template_type,
                content=content,
            )
        },
    )

    with client_request.session_transaction() as session:
        session["recipient"] = recipient
        session["placeholders"] = placeholder_values

    page = client_request.get(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=step_index,
    )

    assert normalize_spaces(page.select_one("label").text) == "name"
    assert normalize_spaces(page.select_one(css_selector_for_content).text) == expected_content


def test_example_spreadsheet(
    client_request,
    mock_get_service_template_with_placeholders_same_as_recipient,
    fake_uuid,
):
    page = client_request.get(".send_messages", service_id=SERVICE_ONE_ID, template_id=fake_uuid)

    assert normalize_spaces(page.select_one("tbody tr").text) == "1 telefoonnummer name date"
    assert page.select_one("input[type=file]").has_attr("accept")
    assert page.select_one("input[type=file]")["accept"] == ".csv,.xlsx,.xls,.ods,.xlsm,.tsv"


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_with_permissions(),
        create_active_caseworking_user(),
    ),
)
def test_send_one_off_offers_link_to_upload(
    client_request,
    fake_uuid,
    mock_get_service_template,
    mock_has_jobs,
    mock_get_no_contact_lists,
    multiple_sms_senders,
    user,
):
    client_request.login(user)

    page = client_request.get(
        "main.send_one_off",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )
    back_link = page.select_one(".govuk-back-link")
    link = page.select_one("form a")

    assert back_link.text.strip() == "Back"

    assert link.text.strip() == "Upload een lijst met telefoonnummers"
    assert link["href"] == url_for(
        "main.send_messages",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


def test_send_one_off_has_link_to_use_existing_list(
    client_request,
    mock_get_service_template,
    mock_has_jobs,
    mock_get_contact_lists,
    multiple_sms_senders,
    fake_uuid,
):
    page = client_request.get(
        "main.send_one_off",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert [(link.text, link["href"]) for link in page.select("form a")] == [
        (
            "Upload een lijst met telefoonnummers",
            url_for(
                "main.send_messages",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
        (
            "Gebruik een noodlijst",
            url_for(
                "main.choose_from_contact_list",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
        (
            "Zie mijn telefoonnummer",
            url_for(
                "main.send_one_off_to_myself",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
    ]


def test_no_link_to_use_existing_list_for_service_without_lists(
    client_request,
    mock_get_service_template,
    mock_has_jobs,
    multiple_sms_senders,
    platform_admin_user,
    fake_uuid,
    mocker,
):
    mocker.patch(
        "app.models.contact_list.ContactLists._get_items",
        return_value=[],
    )
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.send_one_off",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )
    assert [link.text for link in page.select("form a")] == [
        "Upload een lijst met telefoonnummers",
        "Zie mijn telefoonnummer",
    ]


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_with_permissions(),
        create_active_caseworking_user(),
    ),
)
def test_send_one_off_redirects_to_end_if_step_out_of_bounds(
    client_request,
    mock_has_no_jobs,
    mock_get_service_template_with_placeholders,
    fake_uuid,
    user,
):
    client_request.login(user)

    with client_request.session_transaction() as session:
        session["recipient"] = "07900900123"
        session["placeholders"] = {"name": "foo", "telefoonnummer": "07900900123"}

    client_request.get(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=999,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.check_notification",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_with_permissions(),
        create_active_caseworking_user(),
    ),
)
def test_send_one_off_email_to_self_without_placeholders_redirects_to_check_page(
    client_request,
    mocker,
    service_one,
    mock_get_service_email_template_without_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_has_no_jobs,
    fake_uuid,
    user,
):
    mocker.patch("app.user_api_client.get_user", return_value=user)

    with client_request.session_transaction() as session:
        session["recipient"] = "foo@bar.com"
        session["placeholders"] = {"e-mailadres": "foo@bar.com"}

    page = client_request.get(
        "main.send_one_off_step",
        step_index=1,
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert page.select("h1")[0].text.strip() == "Voorbeeld van ‘Two week reminder’"


def test_send_one_off_letter_qr_code_placeholder_too_big(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_service_letter_template_with_qr_placeholder,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mocker,
):
    do_mock_get_page_counts_for_letter(mocker, count=9)
    with client_request.session_transaction() as session:
        session["recipient"] = ""
        session["placeholders"] = {
            "address line 1": "foo",
            "address line 2": "1234 AA",
            "address line 3": "",
            "address line 4": "",
            "address line 5": "",
            "address line 6": "",
        }

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.send_one_off_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=6,
        _data={"placeholder_value": "content which makes the QR code too big " * 25},
        _expected_status=200,
    )

    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Kan geen bruikbare QR-code maken - de ingevoerde tekst maakt de link te lang."
    )


def test_send_one_off_sms_message_puts_submitted_data_in_session(
    client_request,
    service_one,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_contact_lists,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session["recipient"] = "07700 900762"
        session["placeholders"] = {"telefoonnummer": "07700 900762"}

    client_request.post(
        "main.send_one_off_step",
        service_id=service_one["id"],
        template_id=fake_uuid,
        step_index=1,
        _data={"placeholder_value": "Jo"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.check_notification",
            service_id=service_one["id"],
            template_id=fake_uuid,
        ),
    )

    with client_request.session_transaction() as session:
        assert session["recipient"] == "07700 900762"
        assert session["placeholders"] == {"telefoonnummer": "07700 900762", "name": "Jo"}


def test_download_example_csv(
    client_request,
    mock_get_service_template_with_placeholders_same_as_recipient,
    mock_has_permissions,
    fake_uuid,
):
    response = client_request.get_response(
        "main.get_example_csv",
        service_id=fake_uuid,
        template_id=fake_uuid,
        follow_redirects=True,
    )
    assert response.get_data(as_text=True) == "telefoonnummer,name,date\r\n07700 900321,example,example\r\n"
    assert "text/csv" in response.headers["Content-Type"]


@pytest.mark.parametrize("number_of_rows", [1, 11])
def test_check_messages_does_not_allow_to_send_letter_longer_than_10_pages(
    client_request,
    mock_get_service_letter_template,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    mock_get_live_service,
    number_of_rows,
):
    mocker.patch(
        "app.main.views_nl.send.s3download",
        return_value="\n".join(
            ["address_line_1,address_line_2,address_line_3"]
            + ["First Last, 123 Street,1234 HH Den Haag"] * number_of_rows
        ),
    )
    do_mock_get_page_counts_for_letter(mocker, count=11)

    with client_request.session_transaction() as session:
        session["file_uploads"] = {
            fake_uuid: {
                "template_id": "",
            }
        }

    page = client_request.get(
        "main.check_messages",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )
    assert page.select_one("h1", {"data-error-type": "letter-too-long"})

    assert len(page.select(".letter img")) == 10  # if letter longer than 10 pages, only 10 first pages are displayed
    assert not page.select("form button")


def test_send_one_off_letter_address_goes_to_next_placeholder(client_request, mock_template_preview, mocker):
    with client_request.session_transaction() as session:
        session["recipient"] = None
        session["placeholders"] = {}

    template_data = create_template(template_type="letter", content="((foo))")

    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template_data})

    client_request.post(
        "main.send_one_off_letter_address",
        service_id=SERVICE_ONE_ID,
        template_id=template_data["id"],
        _data={"address": "a\nb\n1234AB Den Haag"},
        # step 0-6 represent address line 1-6 and postcode. step 7 is the first non address placeholder
        _expected_redirect=url_for(
            "main.send_one_off_step",
            service_id=SERVICE_ONE_ID,
            template_id=template_data["id"],
            step_index=6,
        ),
    )


@pytest.mark.parametrize(
    ["form_data", "expected_placeholders"],
    [
        # minimal
        (
            "\n".join(["a", "b", "1234 NL Den Haag"]),
            {
                "address_line_1": "a",
                "address_line_2": "b",
                "address_line_3": "",
                "address_line_4": "",
                "address_line_5": "",
                "address_line_6": "1234 NL  DEN HAAG",
                "postcode": "1234 NL",
            },
        ),
        # maximal
        (
            "\n".join(["a", "b", "c", "d", "e", "1234 NL den Haag"]),
            {
                "address_line_1": "a",
                "address_line_2": "b",
                "address_line_3": "c",
                "address_line_4": "d",
                "address_line_5": "e",
                "address_line_6": "1234 NL  DEN HAAG",
                "postcode": "1234 NL",
            },
        ),
        # it ignores empty lines and strips whitespace from each line.
        # It also strips extra whitespace from the middle of lines.
        (
            "\n  a\ta  \n\n\n      \n\n\n\nb  b   \r\n1234 NL Den Haag\n\n",
            {
                "address_line_1": "a a",
                "address_line_2": "b b",
                "address_line_3": "",
                "address_line_4": "",
                "address_line_5": "",
                "address_line_6": "1234 NL  DEN HAAG",
                "postcode": "1234 NL",
            },
        ),
    ],
)
def test_send_one_off_letter_address_populates_address_fields_in_session(
    client_request, fake_uuid, mock_get_service_letter_template, mock_template_preview, form_data, expected_placeholders
):
    with client_request.session_transaction() as session:
        session["recipient"] = None
        session["placeholders"] = {}

    client_request.post(
        "main.send_one_off_letter_address",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={"address": form_data},
        # there are no additional placeholders so go straight to the check page
        _expected_redirect=url_for(
            "main.check_notification",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    with client_request.session_transaction() as session:
        assert session["placeholders"] == expected_placeholders


def test_example_spreadsheet_for_letters(
    client_request,
    service_one,
    mock_get_service_letter_template_with_placeholders,
    fake_uuid,
    mock_get_page_counts_for_letter,
):
    service_one["permissions"] += ["letter"]

    page = client_request.get(".send_messages", service_id=SERVICE_ONE_ID, template_id=fake_uuid)

    assert list(
        zip(
            *[
                [normalize_spaces(cell.text) for cell in page.select("tbody tr")[row].select("th, td")]
                for row in (0, 1)
            ],
            strict=True,
        )
    ) == [
        ("1", "2"),
        ("address line 1", "A. Naam"),
        ("address line 2", "123 Voorbeeldstraat"),
        ("address line 3", "1234 AB Plaats"),
        ("address line 4", ""),
        ("address line 5", ""),
        ("address line 6", ""),
        ("name", "example"),
        ("date", "example"),
    ]
