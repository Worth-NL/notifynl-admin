"""
[NotifyNL] Messagebox CPAs in platform admin: see which CPAs ebms-core holds, upload a new one and select one per
purpose (live: normal API keys to Logius production; team: team keys to Logius pre-production). notifynl-api enforces
the guardrails; these pages only show its verdict.
"""

from urllib.parse import urlsplit

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import user_api_client
from app.main import main
from app.main.overrides_nl.forms import (
    MessageboxCpaSelectConfirmForm,
    MessageboxCpaSelectForm,
    MessageboxCpaUploadConfirmForm,
    MessageboxCpaUploadForm,
)
from app.notify_client.messagebox_cpa_api_client_nl import (
    CPA_PURPOSE_LIVE,
    CPA_PURPOSES,
    CpaRejected,
    messagebox_cpa_api_client,
)
from app.utils.user import user_is_platform_admin
from app.utils_nl.messagebox_cpa_texts import dutch_assessment, dutch_cpa_text, dutch_listing

PURPOSE_NAMES = {
    "live": "Live (productieomgeving van Logius)",
    "team": "Team (pre-productieomgeving van Logius)",
}
PURPOSE_LABELS = {"live": "Live", "team": "Team"}


def _check_purpose(purpose):
    if purpose not in CPA_PURPOSES:
        abort(404)


@main.route("/platform-admin/messagebox-cpas")
@user_is_platform_admin
def messagebox_cpas():
    # the selections live in notifynl-api's database, so they show even when ebms-core can't be reached
    selections = {purpose: messagebox_cpa_api_client.get_selection(purpose) for purpose in CPA_PURPOSES}
    return render_template(
        "views/platform-admin/messagebox-cpas/index.html",
        cpas=_get_cpas(),
        selections=selections,
        purpose_names=PURPOSE_NAMES,
        purpose_labels=PURPOSE_LABELS,
    )


def _get_cpas():
    """Every CPA in ebms-core with Dutch check texts, or None when notifynl-api can't reach ebms-core (its 502)."""
    try:
        cpas = messagebox_cpa_api_client.get_cpas()
    except HTTPError as e:
        if e.status_code < 500:
            raise
        return None
    return [dutch_listing(cpa) for cpa in cpas]


@main.route("/platform-admin/messagebox-cpas/upload", methods=["GET", "POST"])
@user_is_platform_admin
def messagebox_cpa_upload():
    form = MessageboxCpaUploadForm()
    if form.validate_on_submit():
        try:
            # utf-8-sig drops a byte order mark, which ebms-core's parser needn't accept before the XML declaration
            cpa_xml = form.file.data.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            form.file.errors.append("Het bestand is geen UTF-8 XML")
        else:
            return _render_upload_check(cpa_xml, form.purpose.data)

    return render_template("views/platform-admin/messagebox-cpas/upload.html", form=form)


def _render_upload_check(cpa_xml, purpose, rejection=None):
    """Shows the checks for the CPA: from the upload's refusal when it has them, else from validating it."""
    error = rejection.message if rejection else None
    if rejection and rejection.assessment is not None:
        summary, assessment = rejection.summary, rejection.assessment
    else:
        try:
            result = messagebox_cpa_api_client.validate_cpa(cpa_xml, purpose)
            summary, assessment = result["summary"], result["assessment"]
        except CpaRejected as e:
            summary, assessment, error = e.summary, e.assessment, error or e.message

    return render_template(
        "views/platform-admin/messagebox-cpas/upload-check.html",
        summary=summary,
        assessment=dutch_assessment(assessment),
        error=dutch_cpa_text(error),
        purpose_name=PURPOSE_NAMES[purpose],
        form=MessageboxCpaUploadConfirmForm(cpa_xml=cpa_xml, purpose=purpose),
    )


@main.route("/platform-admin/messagebox-cpas/upload/confirm", methods=["POST"])
@user_is_platform_admin
def messagebox_cpa_upload_confirm():
    form = MessageboxCpaUploadConfirmForm()
    if not form.validate_on_submit() or form.purpose.data not in CPA_PURPOSES:
        abort(400)
    try:
        result = messagebox_cpa_api_client.upload_cpa(form.cpa_xml.data, form.purpose.data)
    except CpaRejected as e:
        return _render_upload_check(form.cpa_xml.data, form.purpose.data, rejection=e)

    flash(f"CPA {result['summary']['cpa_id']} staat nu in ebms-core", "default_with_tick")
    return redirect(url_for(".messagebox_cpas"))


@main.route("/platform-admin/messagebox-cpas/<any(live, team):purpose>/select", methods=["GET", "POST"])
@user_is_platform_admin
def messagebox_cpa_select(purpose):
    _check_purpose(purpose)
    cpas = _get_cpas()
    eligible = [cpa for cpa in cpas or [] if _eligible(cpa, purpose)]
    current = messagebox_cpa_api_client.get_selection(purpose)
    form = MessageboxCpaSelectForm(
        [cpa["cpa_id"] for cpa in eligible],
        cpa_id=current["cpa_id"] if current else None,
        message_type=current["message_type"] if current else None,
    )

    if form.validate_on_submit():
        if purpose == CPA_PURPOSE_LIVE:
            # switching live changes where citizen messages go, so it takes a second step
            return render_template(
                "views/platform-admin/messagebox-cpas/select-confirm.html",
                purpose=purpose,
                purpose_name=PURPOSE_NAMES[purpose],
                current=current,
                chosen=next(cpa for cpa in eligible if cpa["cpa_id"] == form.cpa_id.data),
                form=MessageboxCpaSelectConfirmForm(cpa_id=form.cpa_id.data, message_type=form.message_type.data),
            )
        error = _select(purpose, form.cpa_id.data, form.message_type.data)
        if not error:
            return redirect(url_for(".messagebox_cpas"))
        form.cpa_id.errors.append(error)

    history = messagebox_cpa_api_client.get_selection_history(purpose)
    return render_template(
        "views/platform-admin/messagebox-cpas/select.html",
        form=form,
        purpose=purpose,
        purpose_name=PURPOSE_NAMES[purpose],
        ebms_core_unavailable=cpas is None,
        eligible=eligible,
        cpa_hints=[{"hint": {"text": _cpa_hint(cpa, purpose)}} for cpa in eligible],
        current=current,
        history=history,
        user_names=_user_names(entry["updated_by_id"] for entry in history),
    )


@main.route("/platform-admin/messagebox-cpas/<any(live, team):purpose>/select/confirm", methods=["POST"])
@user_is_platform_admin
def messagebox_cpa_select_confirm(purpose):
    _check_purpose(purpose)
    form = MessageboxCpaSelectConfirmForm()
    if not form.validate_on_submit():
        abort(400)
    if error := _select(purpose, form.cpa_id.data, form.message_type.data):
        flash(error, "error")
        return redirect(url_for(".messagebox_cpa_select", purpose=purpose))
    return redirect(url_for(".messagebox_cpas"))


def _cpa_hint(cpa, purpose):
    """What tells CPAs apart when choosing one: where each party receives, how long it's valid and what ends soon."""
    summary = cpa["summary"]
    parties = "; ".join(
        f"{party['name'] or 'Partij'}: {', '.join(map(_host, party['endpoints'])) or 'geen endpoint'}"
        for party in summary["parties"]
    )
    return " ".join(
        [
            f"{parties}.",
            f"Geldig van {summary['start'][:10]} tot {summary['end'][:10]}.",
            *cpa["assessments"][purpose]["warnings"],
        ]
    )


def _host(endpoint):
    return urlsplit(endpoint).hostname or endpoint


def _user_names(user_ids):
    names = {}
    for user_id in set(user_ids) - {None}:
        try:
            names[user_id] = user_api_client.get_user(user_id)["name"]
        except HTTPError as e:
            if e.status_code != 404:
                raise
    return names


def _eligible(cpa, purpose):
    return bool(cpa.get("assessments", {}).get(purpose, {}).get("eligible"))


def _select(purpose, cpa_id, message_type):
    """Selects the CPA; returns notifynl-api's reason when it refuses."""
    try:
        messagebox_cpa_api_client.select_cpa(purpose, cpa_id, message_type, current_user.id)
    except CpaRejected as e:
        failed = [check["message"] for check in (e.assessment or {}).get("checks", []) if not check["passed"]]
        return " ".join(dutch_cpa_text(message) for message in [e.message, *failed])
    flash(f"{PURPOSE_NAMES[purpose]} gebruikt nu CPA {cpa_id}", "default_with_tick")
    return None
