import uuid

import pytest

from app.event_handlers import Events
from tests.app.test_event_handlers import event_dict


def test_update_organisation_letter_provider_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "organisation_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "old_provider": "pingen",
        "new_provider": "rest-endpoint",
        "old_endpoint_url": None,
        "new_endpoint_url": "https://print.example.com/letters",
    }

    Events.update_organisation_letter_provider(**kwargs)

    mock_events.assert_called_with("update_organisation_letter_provider", event_dict(**kwargs))


def test_update_organisation_letter_provider_event_never_takes_credentials(client_request, mock_events):
    with pytest.raises(ValueError):
        Events.update_organisation_letter_provider(
            organisation_id=str(uuid.uuid4()),
            updated_by_id=str(uuid.uuid4()),
            old_provider="pingen",
            new_provider="rest-endpoint",
            old_endpoint_url=None,
            new_endpoint_url="https://print.example.com/letters",
            api_key="secret",
        )

    mock_events.assert_not_called()
