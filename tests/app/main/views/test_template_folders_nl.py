import uuid

import pytest
from notifications_python_client.errors import HTTPError

from tests import sample_uuid
from tests.conftest import SERVICE_ONE_ID

PARENT_FOLDER_ID = "7e979e79-d970-43a5-ac69-b625a8d147b0"
FOLDER_TWO_ID = "bbbb222b-2b22-2b22-222b-b222b22b2222"


def _folder(name, folder_id=None, parent=None, users_with_permission=None):
    return {
        "name": name,
        "id": folder_id or str(uuid.uuid4()),
        "parent_id": parent,
        "users_with_permission": users_with_permission if users_with_permission is not None else [sample_uuid()],
    }


@pytest.mark.parametrize(
    "data",
    [
        {"operation": "move-to-new-folder", "templates_and_folders": [], "move_to_new_folder_name": "foo"},
        {"operation": "move-to-existing-folder", "templates_and_folders": [], "move_to": PARENT_FOLDER_ID},
    ],
)
def test_show_custom_error_message(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
    mock_get_no_api_keys,
    data,
):
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]
    mock_move_to_template_folder.side_effect = HTTPError(message="Some api error msg")

    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
        _expected_redirect=None,
    )

    assert page.select_one("div.banner-dangerous").text.strip() == "Selecteer ten minste één sjabloon of map"
