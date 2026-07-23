from functools import partial
from unittest.mock import ANY

import pytest
from flask import url_for
from notifications_utils.clients.zendesk.zendesk_client import (
    NotifySupportTicket,
    NotifyTicketType,
)

from app.constants import ZendeskTopicId
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from tests.conftest import normalize_spaces


def test_get_support_what_do_you_want_to_do_page(client_request):
    client_request.logout()
    page = client_request.get("main.support_what_do_you_want_to_do")
    assert normalize_spaces(page.select("h1")) == "Wat wilt u doen?"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Meld een probleem"
    assert page.select_one("form input#support_type-0")["value"] == PROBLEM_TICKET_TYPE
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Stel een vraag of geef feedback"
    assert page.select_one("form input#support_type-1")["value"] == QUESTION_TICKET_TYPE
    assert normalize_spaces(page.select_one("form button").text) == "Doorgaan"


def test_get_support_as_someone_in_the_public_sector(
    client_request,
    mocker,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    client_request.logout()
    page = client_request.post(
        "main.support",
        _data={"who": "public-sector"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select("h1")) == "Wat wilt u doen?"
    assert normalize_spaces(page.select_one("form label[for=support_type-0]").text) == "Meld een probleem"
    assert page.select_one("form input#support_type-0")["value"] == PROBLEM_TICKET_TYPE
    assert normalize_spaces(page.select_one("form label[for=support_type-1]").text) == "Stel een vraag of geef feedback"
    assert page.select_one("form input#support_type-1")["value"] == QUESTION_TICKET_TYPE
    assert normalize_spaces(page.select_one("form button").text) == "Doorgaan"


def test_choose_question_support_type_shows_feedback_form(
    client_request, mock_get_non_empty_organisations_and_services_for_user, mocker
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    page = client_request.post(
        "main.support",
        _data={"support_type": QUESTION_TICKET_TYPE},
        _follow_redirects=True,
    )
    assert not page.select_one("input[name=name]")
    assert not page.select_one("input[name=email_address]")
    assert page.select_one("form").find("p").text.strip() == "Wij reageren via test@user.gov.uk"


def test_support_email_address_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_email_address_changed_account_details",
        _data={
            "name": "User",
            "old_email_address": "old_address@gov.uk",
            "new_email_address": "new_address@gov.uk",
        },
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Bedankt voor uw bericht"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Email address has changed",
        message=ANY,
        ticket_type="incident",
        user_name="User",
        user_email="new_address@gov.uk",
        notify_ticket_type=NotifyTicketType.NON_TECHNICAL,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
            {"id": ZendeskTopicId.topic_2, "value": "notify_topic_accessing_2"},
            {"id": ZendeskTopicId.accessing_notify_2, "value": "notify_accessing_service_2"},
        ],
    )


def test_support_no_email_link_account_details_submits_zendesk_ticket(client_request, mocker):
    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mocker.patch(
        "app.main.views_nl.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.logout()
    page = client_request.post(
        "main.support_no_email_link_account_details",
        _data={"name": "User", "email_address": "test@gov.uk"},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Bedankt voor uw bericht"
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="[env: test] Email link not received",
        message=ANY,
        ticket_type="incident",
        user_name="User",
        user_email="test@gov.uk",
        notify_ticket_type=None,
        requester_sees_message_content=False,
        custom_topics=[
            {"id": ZendeskTopicId.topic_1, "value": "notify_topic_accessing"},
            {"id": ZendeskTopicId.accessing_notify_1, "value": "notify_accessing_account"},
        ],
    )


@pytest.mark.parametrize(
    "ticket_type",
    [
        PROBLEM_TICKET_TYPE,
        QUESTION_TICKET_TYPE,
    ],
)
def test_email_address_required_for_problems_and_questions(
    client_request,
    ticket_type,
    mocker,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mocker.patch("app.main.views_nl.feedback.zendesk_client")
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data={"feedback": "blah", "name": "Fred"},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Vul uw e-mailadres in"


@pytest.mark.parametrize(
    "ticket_type",
    [
        PROBLEM_TICKET_TYPE,
        QUESTION_TICKET_TYPE,
    ],
)
def test_name_required_for_problems_and_questions(
    client_request,
    ticket_type,
    mocker,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    mocker.patch("app.main.views_nl.feedback.zendesk_client")
    client_request.logout()
    page = client_request.post(
        "main.feedback",
        ticket_type=ticket_type,
        severe="no",
        _data={"feedback": "blah", "email_address": "me@gov.uk"},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Vul uw naam in"


def test_support_no_security_code_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_security_code_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Vul uw accountgegevens in"

    form_labels = page.select("form label")
    assert len(form_labels) == 3
    assert normalize_spaces(form_labels[0].text) == "Naam"
    assert normalize_spaces(form_labels[1].text) == "E-mailadres"
    assert normalize_spaces(form_labels[2].text) == "Mobiel telefoonnummer"
    assert normalize_spaces(page.select_one("form button").text) == "Versturen"


def test_support_no_security_code_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_no_security_code_account_details",
        _data={"name": "", "email_address": "", "mobile_number": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Vul uw naam in"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Vul uw e-mailadres in"
    assert normalize_spaces(page.select_one("#mobile_number-error").text) == "Error: Vul uw mobiele telefoonnummer in"


def test_support_mobile_number_changed_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_mobile_number_changed_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Vul uw accountgegevens in"

    form_labels = page.select("form label")
    assert len(form_labels) == 4
    assert normalize_spaces(form_labels[0].text) == "Naam"
    assert normalize_spaces(form_labels[1].text) == "E-mailadres"
    assert normalize_spaces(form_labels[2].text) == "Oud mobiel telefoonnummer"
    assert normalize_spaces(form_labels[3].text) == "Nieuw mobiel telefoonnummer"
    assert normalize_spaces(page.select_one("form button").text) == "Versturen"


def test_support_mobile_number_changed_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_mobile_number_changed_account_details",
        _data={"name": "", "email_address": "", "old_mobile_number": "", "new_mobile_number": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Vul uw naam in"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Vul uw e-mailadres in"
    assert (
        normalize_spaces(page.select_one("#old_mobile_number-error").text)
        == "Error: Vul uw oude mobiele telefoonnummer in"
    )
    assert (
        normalize_spaces(page.select_one("#new_mobile_number-error").text)
        == "Error: Vul uw nieuwe mobiele telefoonnummer in"
    )


def test_support_no_email_link_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_email_link_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Vul uw accountgegevens in"

    form_labels = page.select("form label")
    assert len(form_labels) == 2
    assert normalize_spaces(form_labels[0].text) == "Naam"
    assert normalize_spaces(form_labels[1].text) == "E-mailadres"
    assert normalize_spaces(page.select_one("form button").text) == "Versturen"


def test_support_no_email_link_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_no_email_link_account_details",
        _data={"name": "", "email_address": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Vul uw naam in"
    assert normalize_spaces(page.select_one("#email_address-error").text) == "Error: Vul uw e-mailadres in"


def test_support_email_address_changed_account_details_shows_form(client_request):
    client_request.logout()
    page = client_request.get("main.support_email_address_changed_account_details")
    assert normalize_spaces(page.select_one("h1").text) == "Vul uw accountgegevens in"

    form_labels = page.select("form label")
    assert len(form_labels) == 3
    assert normalize_spaces(form_labels[0].text) == "Naam"
    assert normalize_spaces(form_labels[1].text) == "Oud e-mailadres"
    assert normalize_spaces(form_labels[2].text) == "Nieuw e-mailadres"
    assert normalize_spaces(page.select_one("form button").text) == "Versturen"


def test_support_email_address_changed_account_details_form_requires_all_fields(client_request):
    client_request.logout()
    page = client_request.post(
        "main.support_email_address_changed_account_details",
        _data={"name": "", "old_email_address": "", "new_email_address": ""},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("#name-error").text) == "Error: Vul uw naam in"
    assert normalize_spaces(page.select_one("#old_email_address-error").text) == "Error: Vul uw oude e-mailadres in"
    assert normalize_spaces(page.select_one("#new_email_address-error").text) == "Error: Vul uw nieuwe e-mailadres in"


def test_choose_problem_support_type_shows_problem_type_form(
    client_request, mock_get_non_empty_organisations_and_services_for_user, mocker
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    page = client_request.post(
        "main.support",
        _data={"support_type": PROBLEM_TICKET_TYPE},
        _follow_redirects=True,
    )
    assert page.select_one("h1").string.strip() == "Meld een probleem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support")
    assert page.select("form input[type=radio]")[0]["value"] == "sending-messages"
    assert page.select("form input[type=radio]")[1]["value"] == "something-else"


def test_support_problem_when_user_is_logged_in(client_request):
    page = client_request.get("main.support_problem")
    assert page.select_one("h1").string.strip() == "Meld een probleem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 2
    assert radios[0]["value"] == "sending-messages"
    assert radios[1]["value"] == "something-else"


def test_support_problem_when_user_is_logged_out(client_request):
    client_request.logout()
    page = client_request.get("main.support_problem")
    assert page.select_one("h1").string.strip() == "Meld een probleem"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_what_do_you_want_to_do")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 3
    assert radios[0]["value"] == "signing-in"
    assert radios[1]["value"] == "sending-messages"
    assert radios[2]["value"] == "something-else"


def test_support_cannot_sign_in(client_request):
    client_request.logout()
    page = client_request.get("main.support_cannot_sign_in")
    assert page.select_one("h1").string.strip() == "Vertel ons waarom u niet kunt inloggen"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_problem")

    radios = page.select("form input[type=radio]")
    assert len(radios) == 5
    assert radios[0]["value"] == "no-code"
    assert radios[1]["value"] == "mobile-number-changed"
    assert radios[2]["value"] == "no-email-link"
    assert radios[3]["value"] == "email-address-changed"
    assert radios[4]["value"] == "something-else"


def test_support_no_security_code(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_security_code")
    assert normalize_spaces(page.select_one("h1").text) == "Als u geen beveiligingscode heeft ontvangen"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_no_security_code_account_details")}"]')


def test_support_mobile_number_changed(client_request):
    client_request.logout()
    page = client_request.get("main.support_mobile_number_changed")
    assert normalize_spaces(page.select_one("h1").text) == "Als uw mobiele telefoonnummer is gewijzigd"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_mobile_number_changed_account_details")}"]')


def test_support_no_email_link(client_request):
    client_request.logout()
    page = client_request.get("main.support_no_email_link")
    assert normalize_spaces(page.select_one("h1").text) == "Als u geen e-mail met een inloglink heeft ontvangen"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_no_email_link_account_details")}"]')


def test_support_email_address_changed(client_request):
    client_request.logout()
    page = client_request.get("main.support_email_address_changed")
    assert normalize_spaces(page.select_one("h1").text) == "Als uw e-mailadres is gewijzigd"
    assert page.select_one(".govuk-back-link")["href"] == url_for("main.support_cannot_sign_in")
    assert page.select_one(f'a[href="{url_for("main.support_email_address_changed_account_details")}"]')


@pytest.mark.parametrize("user_logged_in", [True, False])
def test_get_support_what_happened_page(client_request, user_logged_in):
    if not user_logged_in:
        client_request.logout()

    page = client_request.get("main.support_what_happened")
    assert page.select_one("h1").string.strip() == "Wat is er gebeurd?"
    assert page.select("form input[type=radio]")[0]["value"] == "technical-difficulties"
    assert page.select("form input[type=radio]")[1]["value"] == "api-500-response"
    assert page.select("form input[type=radio]")[2]["value"] == "something-else"


@pytest.mark.parametrize(
    "extra_args, ticket_type, expected_back_link",
    [
        (
            {"severe": "yes"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support"),
        ),
        ({"severe": "no"}, PROBLEM_TICKET_TYPE, partial(url_for, "main.support")),
        ({"severe": "foo"}, QUESTION_TICKET_TYPE, partial(url_for, "main.support")),  # hacking the URL
        ({}, QUESTION_TICKET_TYPE, partial(url_for, "main.support")),
        ({"severe": "no", "category": "something-else"}, PROBLEM_TICKET_TYPE, partial(url_for, "main.support_problem")),
        (
            {"severe": "no", "category": "problem-sending"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "yes", "category": "tech-error-live-services"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "no", "category": "tech-error-no-live-services"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
        (
            {"severe": "no", "category": "tech-error-signed-out"},
            PROBLEM_TICKET_TYPE,
            partial(url_for, "main.support_what_happened"),
        ),
    ],
)
def test_back_link_from_form(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    extra_args,
    ticket_type,
    expected_back_link,
):
    mocker.patch("app.main.views_nl.feedback.in_business_hours", return_value=True)
    page = client_request.get("main.feedback", ticket_type=ticket_type, **extra_args)
    assert page.select_one(".govuk-back-link")["href"] == expected_back_link()
    h1 = normalize_spaces(page.select_one("h1").text)

    if ticket_type == PROBLEM_TICKET_TYPE:
        assert h1 == "Beschrijf het probleem"
    else:
        assert h1 == "Stel een vraag of geef feedback"
