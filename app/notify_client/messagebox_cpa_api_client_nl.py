"""
[NotifyNL] Messagebox CPAs in platform admin: notifynl-api validates, uploads and selects them, and applies the
guardrails (app/messagebox/cpa_nl.py there). Never cached: a selection decides where citizen messages go.
"""

from contextvars import ContextVar

from flask import current_app
from notifications_python_client.errors import HTTPError
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient

CPA_PURPOSE_LIVE = "live"
CPA_PURPOSE_TEAM = "team"
CPA_PURPOSES = (CPA_PURPOSE_LIVE, CPA_PURPOSE_TEAM)


class CpaRejected(Exception):
    """notifynl-api refused the CPA (400). `assessment` and `summary` say why, when the CPA could be read at all."""

    def __init__(self, message, assessment=None, summary=None):
        super().__init__(message)
        self.message = message
        self.assessment = assessment
        self.summary = summary


def _raise_if_rejected(error: HTTPError):
    """
    Only the guardrails' refusal ({"message": str, ...}) is a CpaRejected. Any other 400, e.g. a schema error
    ({"errors": [...]}) or a body that isn't JSON, stays the HTTPError.
    """
    if error.status_code == 400 and error.response is not None:
        try:
            body = error.response.json()
        except ValueError:
            body = None
        message = body.get("message") if isinstance(body, dict) else None
        if isinstance(message, str):
            raise CpaRejected(message, body.get("assessment"), body.get("summary")) from error
    raise error


class MessageboxCpaApiClient(NotifyAdminAPIClient):
    def get_cpas(self):
        return self.get("/platform-admin/messagebox/cpas")["data"]

    def validate_cpa(self, cpa_xml, purpose):
        try:
            return self.post("/platform-admin/messagebox/cpas/validate", data={"cpa_xml": cpa_xml, "purpose": purpose})[
                "data"
            ]
        except HTTPError as e:
            _raise_if_rejected(e)

    def upload_cpa(self, cpa_xml, purpose):
        try:
            return self.post("/platform-admin/messagebox/cpas", data={"cpa_xml": cpa_xml, "purpose": purpose})["data"]
        except HTTPError as e:
            _raise_if_rejected(e)

    def get_selection(self, purpose):
        return self.get(f"/platform-admin/messagebox/selection/{purpose}")["data"]

    def get_selection_history(self, purpose):
        return self.get(f"/platform-admin/messagebox/selection/{purpose}/history")["data"]

    def select_cpa(self, purpose, cpa_id, message_type, user_id):
        try:
            return self.post(
                f"/platform-admin/messagebox/selection/{purpose}",
                data={"cpa_id": cpa_id, "message_type": message_type, "updated_by_id": str(user_id)},
            )["data"]
        except HTTPError as e:
            _raise_if_rejected(e)


_messagebox_cpa_api_client_context_var: ContextVar[MessageboxCpaApiClient | None] = ContextVar(
    "messagebox_cpa_api_client"
)
get_messagebox_cpa_api_client: LazyLocalGetter[MessageboxCpaApiClient] = LazyLocalGetter(
    _messagebox_cpa_api_client_context_var,
    lambda: MessageboxCpaApiClient(current_app),
)
memo_resetters.append(lambda: get_messagebox_cpa_api_client.clear())
messagebox_cpa_api_client: MessageboxCpaApiClient = LocalProxy(get_messagebox_cpa_api_client)  # type: ignore[assignment]
