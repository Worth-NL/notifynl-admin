from unittest.mock import PropertyMock

import pytest

from app.models.service import Service
from app.utils.branding import get_email_choices
from tests import organisation_json
from tests.conftest import create_email_branding


@pytest.mark.parametrize(
    "org_type, expected_options",
    [
        (
            "central",
            [
                ("rijkshuisstijl", "Rijkshuisstijl"),
                ("rijkshuisstijl_en_org", "Rijkshuisstijl and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "local",
            [
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_org_has_default_branding(
    notify_admin,
    service_one,
    org_type,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type=org_type),
    )
    mocker.patch("app.models.service.Service.email_branding_id")

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_name, expected_options",
    [
        (
            "Rijkshuisstijl en something else",
            [
                ("rijkshuisstijl", "Rijkshuisstijl"),
                ("rijkshuisstijl_en_org", "Rijkshuisstijl en Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "Rijkshuisstijl en test OrganisatioN",
            [
                ("rijkshuisstijl", "Rijkshuisstijl"),
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_branding_name_in_use(
    notify_admin,
    service_one,
    branding_name,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="some-branding-id",
    )
    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value=create_email_branding("_id", {"name": branding_name}),
    )

    options = get_email_choices(service)
    # don't show option if its name is similar to current branding
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_pool, expected_options",
    (
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "Email branding name 1",
                    "text": "Email branding text 1",
                    "id": "email-branding-1-id",
                    "colour": "#f00",
                    "brand_type": "org",
                },
                {
                    "logo": "example_2.png",
                    "name": "Email branding name 2",
                    "text": "Email branding text 2",
                    "id": "email-branding-2-id",
                    "colour": "#f00",
                    "brand_type": "org",
                },
            ],
            [
                ("rijkshuisstijl", "Rijkshuisstijl"),
                ("rijkshuisstijl_en_org", "Rijkshuisstijl en Test Organisation"),
                ("email-branding-2-id", "Email branding name 2"),
            ],
        ),
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "Rijkshuisstijl en Test Organisation",
                    "text": "test organisation",
                    "id": "rijkshuisstijl_en_org",
                    "colour": None,
                    "brand_type": "both",
                },
            ],
            [
                ("rijkshuisstijl", "Rijkshuisstijl"),
                ("rijkshuisstijl_en_org", "Rijkshuisstijl en Test Organisation"),
            ],
        ),
    ),
)
def test_current_email_branding_is_not_displayed_in_email_branding_pool_options(
    notify_admin,
    service_one,
    mock_get_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    branding_pool,
    expected_options,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value="email-branding-1-id",
    )

    mocker.patch("app.models.branding.EmailBrandingPool._get_items", return_value=branding_pool)

    options = get_email_choices(service)
    assert list(options) == expected_options
