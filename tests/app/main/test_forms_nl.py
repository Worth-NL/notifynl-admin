import pytest

from app.main.overrides_nl.forms import AdminServiceAddDataRetentionForm, ServiceLetterContactBlockForm


def test_admin_service_add_data_retention_form_includes_messagebox_choice(notify_admin):
    with notify_admin.test_request_context():
        form = AdminServiceAddDataRetentionForm()
        assert ("messagebox", "Berichtenbox") in form.notification_type.choices


@pytest.mark.parametrize(
    "letter_contact_block, error_expected",
    [
        ("Gemeente Voorbeeld, Postbus 123, 1234 AB Voorbeeldstad", False),
        ("Gemeente Voorbeeld\nPostbus 123", True),
        ("Gemeente Voorbeeld\r\nPostbus 123", True),
    ],
)
def test_service_letter_contact_block_form_rejects_multiline_input(notify_admin, letter_contact_block, error_expected):
    with notify_admin.test_request_context():
        form = ServiceLetterContactBlockForm()
        form.letter_contact_block.data = letter_contact_block
        form.validate()

        if error_expected:
            assert form.errors["letter_contact_block"][0] == "Het adres mag niet meer dan één regel bevatten"
        else:
            assert "letter_contact_block" not in form.errors
