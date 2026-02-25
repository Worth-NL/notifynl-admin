from functools import partial

import pytest
from flask import url_for

from tests import sample_uuid

letters_urls = [
    partial(url_for, "main.edit_service_template", template_id=sample_uuid()),
]


@pytest.mark.parametrize(
    "permissions, choices",
    [
        (["email", "sms", "letter"], ["E-mail", "SMS bericht", "Brief", "Kopieer een bestaand template"]),
        (["email", "sms"], ["E-mail", "SMS bericht", "Kopieer een bestaand template"]),
    ],
)
def test_given_option_to_add_letters_if_allowed(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_organisations_and_services_for_user,
    mock_get_api_keys,
    permissions,
    choices,
):
    service_one["permissions"] = permissions

    page = client_request.get("main.choose_template", service_id=service_one["id"])

    radios = page.select("#add_new_template_form input[type=radio]")
    labels = page.select("#add_new_template_form label")

    assert len(radios) == len(choices)
    assert len(labels) == len(choices)

    for index, choice in enumerate(permissions):
        assert radios[index]["value"] == choice

    for index, label in enumerate(choices):
        assert labels[index].text.strip() == label
