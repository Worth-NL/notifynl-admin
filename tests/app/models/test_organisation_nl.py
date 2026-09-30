import pytest

from app.models.organisation import Organisation
from tests import organisation_json


@pytest.mark.parametrize(
    "letter_provider, expected_identifier",
    [
        (None, "pingen"),
        ({"identifier": "pingen", "address_placement": "60mm"}, "pingen"),
        ({"identifier": "rest-endpoint", "address_placement": "50mm"}, "rest-endpoint"),
    ],
)
def test_organisation_letter_provider(letter_provider, expected_identifier):
    organisation = Organisation(organisation_json(letter_provider=letter_provider))

    assert organisation.letter_provider == letter_provider
    assert organisation.letter_provider_identifier == expected_identifier


def test_set_letter_provider_clears_the_organisations_cached_services(notify_admin, mocker):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[{"id": "service-1", "name": "a"}, {"id": "service-2", "name": "b"}],
    )
    mock_set = mocker.patch("app.organisations_client.set_organisation_letter_provider")
    organisation = Organisation(organisation_json(id_="org-1"))

    organisation.set_letter_provider(provider="pingen", updated_by_id="user-1")

    mock_set.assert_called_once_with(
        "org-1", {"provider": "pingen", "updated_by_id": "user-1"}, cached_service_ids=["service-1", "service-2"]
    )
