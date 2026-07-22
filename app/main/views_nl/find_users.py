from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from markupsafe import Markup
from notifications_python_client.errors import HTTPError

from app import user_api_client
from app.event_handlers import Events
from app.main import main
from app.main.overrides_nl.forms import AuthTypeForm
from app.models.user import User
from app.utils.user import user_is_platform_admin


@main.route("/users/<uuid:user_id>", methods=["GET"])
@user_is_platform_admin
def user_information(user_id):
    return render_template(
        "views/find-users/user-information.html",
        user=User.from_id(user_id),
    )


@main.route("/users/<uuid:user_id>/remove-platform-admin", methods=["GET", "POST"])
@user_is_platform_admin
def remove_platform_admin(user_id):
    if request.method == "POST":
        User.from_id(user_id).remove_platform_admin()
        Events.remove_platform_admin(user_id=str(user_id), removed_by_id=current_user.id)
        return redirect(url_for(".user_information", user_id=user_id))

    flash("Weet u zeker dat u de platformbeheerdersrechten van deze gebruiker wilt verwijderen?", "remove")
    return user_information(user_id)


@main.route("/users/<uuid:user_id>/archive", methods=["GET", "POST"])
@user_is_platform_admin
def archive_user(user_id):
    if request.method == "POST":
        user = User.from_id(user_id)
        original_email_address = user.email_address

        try:
            user_api_client.archive_user(user_id)
        except HTTPError as e:
            if e.status_code == 400 and "User cannot be removed from a service" in e.message:
                flash(
                    Markup(
                        """
                        <h2 class='govuk-heading-m'>U kunt deze gebruiker niet archiveren</h2>
                        <p class='govuk-body error-text-colour govuk-!-font-weight-bold'>
                            Deze gebruiker heeft voor ten minste één dienst de rechten om instellingen te beheren.
                        </p>
                        <p class='govuk-body error-text-colour govuk-!-font-weight-bold'>
                            Als de gebruiker wil dat wij hun dienst(en) verwijderen, volg dan de instructies in de
                            ondersteuningshandleiding en probeer het daarna opnieuw.
                        </p>
                        <p class='govuk-body error-text-colour govuk-!-font-weight-bold'>
                            Zo niet, vraag hen dan om nieuwe teamleden toe te voegen of de rechten van hun team(s)
                            bij te werken, en probeer het daarna opnieuw.
                        </p>
                        """
                    )
                )
                return redirect(url_for("main.user_information", user_id=user_id))

        Events.archive_user(
            user_id=str(user_id), user_email_address=original_email_address, archived_by_id=current_user.id
        )

        return redirect(url_for(".user_information", user_id=user_id))
    else:
        flash("Dit kan niet ongedaan worden gemaakt! Weet u zeker dat u deze gebruiker wilt archiveren?", "delete")
        return user_information(user_id)


@main.route("/users/<uuid:user_id>/change-auth", methods=["GET", "POST"])
@user_is_platform_admin
def change_user_auth(user_id):
    user = User.from_id(user_id)
    if user.webauthn_auth:
        abort(403)

    form = AuthTypeForm(auth_type=user.auth_type)

    if form.validate_on_submit():
        user.update(auth_type=form.auth_type.data)
        return redirect(url_for(".user_information", user_id=user_id))

    return render_template(
        "views/find-users/auth_type.html",
        form=form,
        user=user,
    )
