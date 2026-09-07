import pytest
from flask import url_for

from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID


@pytest.mark.parametrize(
    "brand_type, expected_name",
    (
        ("org", "some alt text"),
        ("both", "Rijkshuisstijl and some alt text"),
    ),
)
def test_POST_email_branding_set_alt_text_creates_branding_adds_to_pool_and_redirects(
    client_request,
    service_one,
    mock_get_organisation,
    mock_create_email_branding,
    mock_get_email_branding_name_for_alt_text,
    active_user_with_permissions,
    mock_update_service,
    fake_uuid,
    mocker,
    brand_type,
    expected_name,
):
    service_one["organisation"] = ORGANISATION_ID
    mock_flash = mocker.patch("app.main.views_nl.service_settings.branding.flash")
    mocker.patch(
        "app.main.views_nl.service_settings.branding.logo_client.save_permanent_logo",
        return_value="permanent-example.png",
    )
    mocker.patch(
        "app.main.views_nl.service_settings.branding._should_set_default_org_email_branding",
        return_value=False,
    )
    mocker.patch(
        "app.organisations_client.add_brandings_to_email_branding_pool",
        return_value=None,
    )
    client_request.post(
        "main.email_branding_set_alt_text",
        service_id=service_one["id"],
        brand_type=brand_type,
        logo="example.png",
        _data={"alt_text": "some alt text"},
        _expected_status=302,
        _expected_redirect=url_for("main.service_settings", service_id=SERVICE_ONE_ID),
    )
    mock_flash.assert_called_once_with(
        "Uw e-mailhuisstijl is gewijzigd. Stuur uzelf een e-mail om te controleren of alles er goed uitziet.",
        "default_with_tick",
    )
