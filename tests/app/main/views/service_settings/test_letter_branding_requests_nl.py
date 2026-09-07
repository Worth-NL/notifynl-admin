from flask import url_for

from app.models.branding import LetterBranding
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


def test_letter_branding_nhs_changes_letter_branding_when_user_confirms(
    service_one,
    organisation_one,
    client_request,
    no_reply_to_email_addresses,
    single_sms_sender,
    mock_get_letter_branding_pool,
    mock_update_service,
    mocker,
):
    organisation_one["organisation_type"] = "nhs_central"
    service_one["organisation"] = organisation_one

    mock_flash = mocker.patch("app.main.views_nl.service_settings.branding.flash")
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_one,
    )

    client_request.post(
        ".branding_nhs",
        service_id=SERVICE_ONE_ID,
        branding_type="letter",
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        letter_branding=LetterBranding.NHS_ID,
    )
    mock_flash.assert_called_once_with("Uw briefhuisstijl is bijgewerkt", "default")
