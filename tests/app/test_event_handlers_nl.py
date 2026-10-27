import uuid

import pytest

from app.event_handlers import Events
from tests.app.test_event_handlers import event_dict


def _letter_provider_event_kwargs():
    return {
        "organisation_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "old_provider": "pingen",
        "new_provider": "rest-endpoint",
        "old_endpoint_url": None,
        "new_endpoint_url": "https://print.example.com/letters",
        "old_auth_method": None,
        "new_auth_method": "oauth",
        "old_auth_config": {},
        "new_auth_config": {"token_endpoint": "https://login.example.com/token", "client_id": "notify"},
        "old_address_placement": "60mm",
        "new_address_placement": "50mm",
        "credentials_entered": True,
    }


def test_update_organisation_letter_provider_event_calls_events_api(client_request, mock_events):
    kwargs = _letter_provider_event_kwargs()

    Events.update_organisation_letter_provider(**kwargs)

    mock_events.assert_called_with("update_organisation_letter_provider", event_dict(**kwargs))


@pytest.mark.parametrize("credential", ["api_key", "password", "client_secret"])
def test_update_organisation_letter_provider_event_never_takes_credentials(client_request, mock_events, credential):
    with pytest.raises(TypeError):
        Events.update_organisation_letter_provider(**_letter_provider_event_kwargs(), **{credential: "secret"})

    mock_events.assert_not_called()
