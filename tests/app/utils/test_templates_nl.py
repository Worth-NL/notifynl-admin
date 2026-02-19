from unittest import mock

import pytest
from bs4 import BeautifulSoup
from freezegun import freeze_time
from markupsafe import Markup

from app import load_service_before_request
from app.utils.templates import EmailPreviewTemplate, TemplatedLetterImageTemplate
from tests.conftest import SERVICE_ONE_ID, do_mock_get_page_counts_for_letter


@pytest.fixture(scope="function", autouse=True)
def app_context(notify_admin, fake_uuid, mock_get_service, mock_get_page_counts_for_letter):
    with notify_admin.test_request_context(f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}"):
        load_service_before_request()
        yield notify_admin


def test_letter_image_renderer_requires_valid_postage():
    with pytest.raises(TypeError) as exception:
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter", "postage": "third"},
            image_url="foo",
        )
    assert str(exception.value) == ("postage must be None, 'netherlands', 'europe' or 'rest-of-world'")


@pytest.mark.parametrize(
    "initial_postage_value",
    (
        {},
        {"postage": None},
        {"postage": "netherlands"},
        {"postage": "europe"},
        {"postage": "rest-of-world"},
    ),
)
@pytest.mark.parametrize(
    "postage_value",
    (
        None,
        "netherlands",
        "europe",
        "rest-of-world",
        pytest.param("other", marks=pytest.mark.xfail(raises=TypeError)),
    ),
)
def test_letter_image_renderer_postage_can_be_overridden(initial_postage_value, postage_value):
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter"} | initial_postage_value
    )
    assert template.postage == initial_postage_value.get("postage")

    template.postage = postage_value
    assert template.postage == postage_value


@pytest.mark.parametrize(
    "postage, expected_attribute_value, expected_postage_text",
    (
        (None, None, None),
        (
            "netherlands",
            ["letter-postage", "letter-postage-national"],
            "Frankering: national",
        ),
        (
            "europe",
            ["letter-postage", "letter-postage-international"],
            "Frankering: international",
        ),
        (
            "rest-of-world",
            ["letter-postage", "letter-postage-international"],
            "Frankering: international",
        ),
    ),
)
def test_letter_image_renderer_passes_postage_to_html_attribute(
    postage,
    expected_attribute_value,
    expected_postage_text,
):
    template = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {
                    "service": SERVICE_ONE_ID,
                    "content": "",
                    "subject": "",
                    "template_type": "letter",
                    "postage": postage,
                },
                image_url="foo",
            )
        ),
        features="html.parser",
    )
    if expected_attribute_value:
        assert template.select_one(".letter-postage")["class"] == expected_attribute_value
        assert template.select_one(".letter-postage").text.strip() == expected_postage_text
    else:
        assert not template.select(".letter-postage")


@freeze_time("2012-12-12 12:12:12")
@pytest.mark.parametrize(
    "page_count, expected_oversized, expected_page_numbers",
    [
        (
            1,
            False,
            [1],
        ),
        (
            5,
            False,
            [1, 2, 3, 4, 5],
        ),
        (
            10,
            False,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
        (
            11,
            True,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
        (
            99,
            True,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
    ],
)
@pytest.mark.parametrize(
    "postage_args, expected_show_postage, expected_postage_class_value, expected_postage_description",
    (
        pytest.param({}, False, None, None),
        pytest.param({"postage": None}, False, None, None),
        pytest.param({"postage": "netherlands"}, True, "letter-postage-national", "national"),
        pytest.param({"postage": "europe"}, True, "letter-postage-international", "international"),
        pytest.param({"postage": "rest-of-world"}, True, "letter-postage-international", "international"),
        pytest.param(
            {"postage": "third"},
            True,
            "letter-postage-third",
            "third class",
            marks=pytest.mark.xfail(raises=TypeError),
        ),
    ),
)
def test_letter_image_renderer(
    mocker,
    page_count,
    expected_page_numbers,
    expected_oversized,
    postage_args,
    expected_show_postage,
    expected_postage_class_value,
    expected_postage_description,
):
    do_mock_get_page_counts_for_letter(mocker, count=page_count)
    mock_render = mocker.patch("app.utils.templates.render_template")
    str(
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "Content", "subject": "Subject", "template_type": "letter"}
            | postage_args,
            image_url="http://example.com/endpoint.png",
            contact_block="10 Downing Street",
        )
    )
    assert mock_render.call_args_list == [
        mocker.call(
            mocker.ANY,
            image_url="http://example.com/endpoint.png",
            page_numbers=expected_page_numbers,
            first_page_of_attachment=None,
            first_page_of_english=1,
            address=[
                Markup("<span class='placeholder-no-brackets'>address line 1</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 2</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 3</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 4</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 5</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 6</span>"),
            ],
            contact_block="10 Downing Street",
            date="12 December 2012",
            subject="Subject",
            message="<p>Content</p>",
            show_postage=expected_show_postage,
            postage_class_value=expected_postage_class_value,
            postage_description=expected_postage_description,
            template=mocker.ANY,
        )
    ]


@pytest.mark.parametrize(
    "template_class, template_type, extra_args, expected_field_calls",
    [
        (
            EmailPreviewTemplate,
            "email",
            {},
            [
                mock.call("content", {}, html="escape", markdown_lists=True, redact_missing_personalisation=False),
                mock.call("subject", {}, html="escape", redact_missing_personalisation=False),
                mock.call("((email address))", {}, with_brackets=False),
            ],
        ),
        (
            EmailPreviewTemplate,
            "email",
            {"redact_missing_personalisation": True},
            [
                mock.call("content", {}, html="escape", markdown_lists=True, redact_missing_personalisation=True),
                mock.call("subject", {}, html="escape", redact_missing_personalisation=True),
                mock.call("((email address))", {}, with_brackets=False),
            ],
        ),
        (
            TemplatedLetterImageTemplate,
            "letter",
            {"image_url": "http://example.com", "contact_block": "www.gov.uk"},
            [
                mock.call(
                    (
                        "((address line 1))\n"
                        "((address line 2))\n"
                        "((address line 3))\n"
                        "((address line 4))\n"
                        "((address line 5))\n"
                        "((address line 6))"
                    ),
                    {},
                    with_brackets=False,
                    html="escape",
                ),
                mock.call("www.gov.uk", {}, html="escape", redact_missing_personalisation=False),
                mock.call("subject", {}, html="escape", redact_missing_personalisation=False),
                mock.call("content", {}, html="escape", markdown_lists=True, redact_missing_personalisation=False),
            ],
        ),
    ],
)
@mock.patch("notifications_utils.template.Field.__init__", return_value=None)
@mock.patch("notifications_utils.template.Field.__str__", return_value="1\n2\n3\n4\n5\n6\n7\n8")
def test_templates_handle_html_and_redacting(
    mock_field_str,
    mock_field_init,
    template_class,
    template_type,
    extra_args,
    expected_field_calls,
):
    assert str(
        template_class(
            {"service": SERVICE_ONE_ID, "content": "content", "subject": "subject", "template_type": template_type},
            **extra_args,
        )
    )
    assert mock_field_init.call_args_list == expected_field_calls


@freeze_time("2012-12-12 12:12:12")
@pytest.mark.parametrize(
    "postage_argument",
    (
        None,
        "netherlands",
        "europe",
        "rest-of-world",
    ),
)
def test_letter_image_renderer_shows_international_post(
    mocker,
    postage_argument,
):
    mock_render = mocker.patch("app.utils.templates.render_template")
    str(
        TemplatedLetterImageTemplate(
            {
                "service": SERVICE_ONE_ID,
                "content": "Content",
                "subject": "Subject",
                "template_type": "letter",
                "postage": postage_argument,
            },
            {
                "address line 1": "123 Example Street",
                "address line 2": "Lima",
                "address line 3": "Peru",
            },
            image_url="http://example.com/endpoint.png",
        )
    )
    assert mock_render.call_args_list[0][1]["postage_description"] == "international"
