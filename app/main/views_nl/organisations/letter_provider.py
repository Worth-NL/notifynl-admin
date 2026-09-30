from flask import current_app, redirect, render_template, url_for
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
from app.utils.user import user_has_permissions

# Any member of the organisation can choose its letter provider, not just platform admins


@main.route("/organisations/<uuid:org_id>/letter-provider", methods=["GET"])
@user_has_permissions()
def organisation_letter_provider(org_id):
    return render_template(
        "views/organisations/organisation/letter-provider/index.html",
        letter_provider=organisations_client.get_organisation_letter_provider(org_id),
    )


@main.route("/organisations/<uuid:org_id>/letter-provider/change", methods=["GET", "POST"])
@user_has_permissions()
def organisation_change_letter_provider(org_id):
    form = OrganisationLetterProviderForm(provider=current_organisation.letter_provider_identifier)

    if form.validate_on_submit():
        if form.provider.data == "rest-endpoint":
            return redirect(url_for(".organisation_letter_endpoint", org_id=org_id))

        stored = organisations_client.get_organisation_letter_provider(org_id)
        if not stored or stored["identifier"] != "pingen":
            _save_letter_provider({"provider": "pingen"}, stored)
        return redirect(url_for(".organisation_letter_provider", org_id=org_id))

    return render_template("views/organisations/organisation/letter-provider/change.html", form=form)


@main.route("/organisations/<uuid:org_id>/letter-provider/rest-endpoint", methods=["GET", "POST"])
@user_has_permissions()
def organisation_letter_endpoint(org_id):
    stored = organisations_client.get_organisation_letter_provider(org_id)
    stored_endpoint = stored if stored and stored["identifier"] == "rest-endpoint" else None
    form = OrganisationLetterEndpointForm(
        stored=stored_endpoint,
        allow_insecure=current_app.config.get("LETTER_ENDPOINT_ALLOW_INSECURE", False),
        **_form_data(stored_endpoint),
    )

    if form.validate_on_submit():
        try:
            _save_letter_provider(form.api_data(), stored)
        except HTTPError as e:
            if e.status_code != 400:
                raise
            form.add_api_error(e.message)
        else:
            return redirect(url_for(".organisation_letter_provider", org_id=org_id))

    return render_template(
        "views/organisations/organisation/letter-provider/rest-endpoint.html",
        form=form,
        has_stored_endpoint=bool(stored_endpoint),
    )


def _form_data(stored_endpoint):
    if not stored_endpoint:
        return {"address_placement": "60mm"}

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
    Events.update_organisation_letter_provider(
        organisation_id=current_organisation.id,
        updated_by_id=current_user.id,
        old_provider=stored["identifier"] if stored else None,
        new_provider=letter_provider["identifier"],
        old_endpoint_url=stored["endpoint_url"] if stored else None,
        new_endpoint_url=letter_provider["endpoint_url"],
    )
