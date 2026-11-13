import hashlib
import hmac
import json
import time
from uuid import UUID

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import current_organisation, organisations_client
from app.event_handlers import Events
from app.main import main
from app.main.overrides_nl.forms import (
    LETTER_ENDPOINT_AUTH_FIELDS,
    LETTER_ENDPOINT_DUMMY_SECRET,
    LETTER_ENDPOINT_SECRET_FIELDS,
    OrganisationLetterEndpointForm,
    OrganisationLetterProviderForm,
)
from app.main.views_nl.organisations.index import organisation_settings
from app.utils.user import user_has_permissions

# Any member of the organisation can choose its letter provider, not just platform admins. Its summary is a section
# of the organisation's settings page, which org members see with nothing else on it.

# requests are cut off after HTTP_SERVE_TIMEOUT_SECONDS (30 by default): a test not done by then can be looked up again
CONNECTION_TEST_WAIT_SECONDS = 20
CONNECTION_TEST_POLL_SECONDS = 1


@main.route("/organisations/<uuid:org_id>/letter-provider/change", methods=["GET", "POST"])
@user_has_permissions()
def organisation_change_letter_provider(org_id):
    form = OrganisationLetterProviderForm(provider=current_organisation.letter_provider_identifier)

    if form.validate_on_submit():
        if form.provider.data == "rest-endpoint":
            return redirect(url_for(".organisation_letter_endpoint", org_id=org_id))

        stored = organisations_client.get_organisation_letter_provider(org_id)
        if _is_rest_endpoint(stored):
            return redirect(url_for(".organisation_confirm_pingen_letter_provider", org_id=org_id))
        if not stored or stored["identifier"] != "pingen":
            _save_letter_provider({"provider": "pingen"}, stored)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/letter-provider/change.html",
        form=form,
        has_stored_endpoint=current_organisation.letter_provider_identifier == "rest-endpoint",
    )


@main.route("/organisations/<uuid:org_id>/letter-provider/pingen", methods=["GET", "POST"])
@user_has_permissions()
def organisation_confirm_pingen_letter_provider(org_id):
    # switching to Pingen makes notifynl-api delete the endpoint's settings and login details, so ask first
    stored = organisations_client.get_organisation_letter_provider(org_id)
    if not _is_rest_endpoint(stored):
        return redirect(url_for(".organisation_change_letter_provider", org_id=org_id))

    if request.method == "POST":
        _save_letter_provider({"provider": "pingen"}, stored)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    flash(
        "Weet u zeker dat u naar Pingen wilt overstappen? NotifyNL verwijdert dan de instellingen en inloggegevens "
        "van uw eigen printleverancier. Die moet u opnieuw invullen als u later terug wilt.",
        "delete",
    )
    return organisation_settings(org_id)


@main.route("/organisations/<uuid:org_id>/letter-provider/rest-endpoint", methods=["GET", "POST"])
@user_has_permissions()
def organisation_letter_endpoint(org_id):
    stored = organisations_client.get_organisation_letter_provider(org_id)
    stored_endpoint = stored if _is_rest_endpoint(stored) else None
    form = OrganisationLetterEndpointForm(
        stored=stored_endpoint,
        allow_insecure=current_app.config.get("LETTER_ENDPOINT_ALLOW_INSECURE", False),
        **_form_data(stored_endpoint),
    )

    connection_test = None
    if form.validate_on_submit():
        try:
            connection_test = _connection_test_from_request(form)
            if connection_test is None:
                _save_letter_provider(form.api_data(), stored)
        except HTTPError as e:
            if e.status_code != 400:
                raise
            form.add_api_error(e.message)
        else:
            if connection_test is None:
                return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/letter-provider/rest-endpoint.html",
        form=form,
        has_stored_endpoint=bool(stored_endpoint),
        connection_test=connection_test,
    )


def _connection_test_from_request(form):
    """The result to show if one of the connection test buttons was pressed, otherwise None. Never saves anything."""
    connection_test_id = request.form.get("connection_test_id")
    if not connection_test_id and "test_connection" not in request.form:
        return None
    if not current_user.platform_admin:
        # a test presents NotifyNL's client certificate to the host that was typed in, and shows its reply
        abort(403)

    try:
        if connection_test_id:
            return _look_up_connection_test_again(_uuid_or_404(connection_test_id), form)
        return _start_connection_test(form)
    except HTTPError as e:
        if e.status_code == 409:
            return {"state": "busy"}
        if e.status_code == 429:
            return {"state": "rate_limited"}
        if e.status_code == 503:
            return {"state": "unavailable"}
        raise


def _start_connection_test(form):
    tested_values = _tested_values(form)
    connection_test_id = organisations_client.start_letter_endpoint_connection_test(
        current_organisation.id, tested_values | {"started_by_id": current_user.id}
    )["id"]
    Events.start_letter_endpoint_connection_test(
        organisation_id=current_organisation.id,
        started_by_id=current_user.id,
        connection_test_id=connection_test_id,
        endpoint_url=tested_values["endpoint_url"],
        token_endpoint=tested_values["auth_config"].get("token_endpoint"),
        auth_method=tested_values["auth_method"],
    )
    return _wait_for_connection_test(connection_test_id) | {"tested_values": _signature(tested_values)}


def _look_up_connection_test_again(connection_test_id, form):
    result = _wait_for_connection_test(connection_test_id)
    signature = request.form.get("tested_values")
    if not signature:
        return result
    # the result is of the values the test started with, and the form may have been edited since
    return result | {
        "tested_values": signature,
        "values_changed": not hmac.compare_digest(signature, _signature(_tested_values(form))),
    }


def _tested_values(form):
    data = form.api_data()
    return {
        "endpoint_url": data["endpoint_url"],
        "auth_method": data["auth_method"],
        "auth_config": data["auth_config"],
    }


def _signature(tested_values):
    """Tells whether the form still holds the tested values, without the secrets among them being readable from it."""
    message = b"letter-endpoint-connection-test:" + json.dumps(tested_values, sort_keys=True).encode()
    return hmac.new(current_app.config["SECRET_KEY"].encode(), message, hashlib.sha256).hexdigest()


def _wait_for_connection_test(connection_test_id):
    deadline = time.monotonic() + CONNECTION_TEST_WAIT_SECONDS
    while True:
        try:
            result = organisations_client.get_letter_endpoint_connection_test(
                current_organisation.id, connection_test_id
            )
        except HTTPError as e:
            if e.status_code == 404:
                return {"state": "expired"}
            raise
        if result["state"] == "finished" or time.monotonic() >= deadline:
            return result | {"id": connection_test_id}
        time.sleep(CONNECTION_TEST_POLL_SECONDS)


def _uuid_or_404(value):
    try:
        return str(UUID(value))
    except ValueError:
        abort(404)


def _is_rest_endpoint(stored):
    return bool(stored) and stored["identifier"] == "rest-endpoint"


def _form_data(stored_endpoint):
    if not stored_endpoint:
        return {"address_placement": "50mm"}  # 60mm is only for Pingen

    auth_method = stored_endpoint["auth_method"]
    data = {
        "endpoint_url": stored_endpoint["endpoint_url"],
        "address_placement": stored_endpoint["address_placement"],
        "auth_method": auth_method,
        **{name: value for name, value in stored_endpoint["auth_config"].items() if value},
    }
    if stored_endpoint["has_credentials"]:
        for name in LETTER_ENDPOINT_AUTH_FIELDS.get(auth_method, ()):
            if name in LETTER_ENDPOINT_SECRET_FIELDS:
                data[name] = LETTER_ENDPOINT_DUMMY_SECRET
    return data


def _save_letter_provider(data, stored):
    letter_provider = current_organisation.set_letter_provider(**data, updated_by_id=current_user.id)
    stored = stored or {}
    Events.update_organisation_letter_provider(
        organisation_id=current_organisation.id,
        updated_by_id=current_user.id,
        old_provider=stored.get("identifier"),
        new_provider=letter_provider["identifier"],
        old_endpoint_url=stored.get("endpoint_url"),
        new_endpoint_url=letter_provider["endpoint_url"],
        old_auth_method=stored.get("auth_method"),
        new_auth_method=letter_provider["auth_method"],
        old_auth_config=_without_secrets(stored.get("auth_config")),
        new_auth_config=_without_secrets(letter_provider.get("auth_config")),
        old_address_placement=stored.get("address_placement"),
        new_address_placement=letter_provider["address_placement"],
        # only whether login details were typed in: the secrets themselves never go in the event
        credentials_entered=any(data.get("auth_config", {}).get(name) for name in LETTER_ENDPOINT_SECRET_FIELDS),
    )


def _without_secrets(auth_config):
    # notifynl-api never returns secrets, but the audit event mustn't rely on that
    return {name: value for name, value in (auth_config or {}).items() if name not in LETTER_ENDPOINT_SECRET_FIELDS}
