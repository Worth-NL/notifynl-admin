from tests.conftest import (
    SERVICE_ONE_ID,
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
