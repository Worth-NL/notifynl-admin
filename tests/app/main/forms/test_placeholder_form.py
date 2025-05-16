import pytest

from app.main.forms import get_placeholder_form_instance


def test_form_class_not_mutated(notify_admin):
    with notify_admin.test_request_context(method="POST", data={"placeholder_value": ""}):
        form1 = get_placeholder_form_instance("name", {}, "sms")
        form2 = get_placeholder_form_instance("city", {}, "sms")

        assert not form1.validate_on_submit()
        assert not form2.validate_on_submit()

        assert str(form1.placeholder_value.label) == '<label for="placeholder_value">name</label>'
        assert str(form2.placeholder_value.label) == '<label for="placeholder_value">city</label>'


@pytest.mark.parametrize(
    "service_can_send_international_sms, send_to_uk_landlines, placeholder_name, template_type, value, expected_error",
    [
        (False, False, "email address", "email", "", "Enter an email address"),
        (
            False,
            False,
            "email address",
            "email",
            "12345",
            "Enter an email address in the correct format, like name@example.gov.uk",
        ),
        (
            False,
            False,
            "email address",
            "email",
            "“bad”@email-address.com",
            "Enter an email address in the correct format, like name@example.gov.uk",
        ),
        (False, False, "email address", "email", "test@example.com", None),
        (False, False, "email address", "email", "test@example.gov.uk", None),
        (False, False, "phone number", "sms", "", "Cannot be empty"),
        (
            False,
            False,
            "phone number",
            "sms",
            "+1-2345-678890",
            "This does not look like a UK mobile number – double check the mobile number you entered",
        ),
        (False, False, "phone number", "sms", "07900900123", None),
        (False, False, "phone number", "sms", "+44(0)7900 900-123", None),
        (True, False, "phone number", "sms", "+123", "Mobile number is too short"),
        (True, False, "phone number", "sms", "+44(0)7900 900-123", None),
        (True, False, "phone number", "sms", "+1-2345-678890", None),
        (False, False, "anything else", "sms", "", "Cannot be empty"),
        (False, False, "anything else", "email", "", "Cannot be empty"),
        (True, False, "phone number", "sms", "invalid", "Mobile numbers can only include: 0 1 2 3 4 5 6 7 8 9 ( ) + -"),
        (True, False, "phone number", "email", "invalid", None),
        (True, False, "phone number", "letter", "invalid", None),
        (True, False, "email address", "sms", "invalid", None),
        (False, True, "phone number", "sms", "02030024300", None),
    ],
)
@pytest.mark.skip(reason="[NOTIFYNL] Dutch phone number implementation breaks this test")
def test_validates_recipients(
    notify_admin,
    placeholder_name,
    template_type,
    value,
    service_can_send_international_sms,
    send_to_uk_landlines,
    expected_error,
):
    with notify_admin.test_request_context(method="POST", data={"placeholder_value": value}):
        form = get_placeholder_form_instance(
            placeholder_name,
            {},
            template_type,
            allow_international_phone_numbers=service_can_send_international_sms,
            allow_sms_to_uk_landline=send_to_uk_landlines,
        )
        if expected_error:
            assert not form.validate_on_submit()
            assert form.placeholder_value.errors[0] == expected_error
        else:
            assert form.validate_on_submit()
