from app.main.overrides_nl.forms import AdminServiceAddDataRetentionForm


def test_admin_service_add_data_retention_form_includes_messagebox_choice(notify_admin):
    with notify_admin.test_request_context():
        form = AdminServiceAddDataRetentionForm()
        assert ("messagebox", "Berichtenbox") in form.notification_type.choices
