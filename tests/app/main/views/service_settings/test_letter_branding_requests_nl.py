from flask import url_for

from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID


def test_POST_letter_branding_set_name_creates_branding_adds_to_pool_and_redirects(
    client_request,
    service_one,
    mock_create_letter_branding,
    mock_get_organisation,
    mock_update_service,
    fake_uuid,
    mocker,
):
    service_one["organisation"] = ORGANISATION_ID
    mock_flash = mocker.patch("app.main.views_nl.service_settings.branding.flash")
    mocker.patch(
        "app.main.views_nl.service_settings.branding.letter_branding_client.get_unique_name_for_letter_branding",
        return_value="some unique name",
    )
    mocker.patch(
        "app.main.views_nl.service_settings.branding._should_set_default_org_letter_branding", return_value=False
    )
    mocker.patch(
        "app.main.views_nl.service_settings.branding.logo_client.save_permanent_logo", return_value="permanent.svg"
    )
    mocker.patch("app.organisations_client.add_brandings_to_letter_branding_pool", return_value=None)

    client_request.post(
        "main.letter_branding_set_name",
        service_id=SERVICE_ONE_ID,
        temp_filename="temporary.svg",
        branding_choice="something else",
        _data={"name": "some name"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    mock_flash.assert_called_once_with(
        "Uw briefhuisstijl is gewijzigd.",
        "default_with_tick",
    )
