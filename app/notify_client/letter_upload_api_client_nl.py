"""
[NotifyNL] Checks a letter uploaded in admin ("Upload een brief") through notifynl-api, which decides the address
window it's checked against and whether the service may send international letters, and asks template-preview.
"""

import base64
from contextvars import ContextVar
from io import BytesIO

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from notifications_utils.pdf import extract_page_from_pdf
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class SanitisedLetter:
    """template-preview's answer, as the API passes it on: its status (400 when the letter is invalid) and JSON."""

    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class LetterUploadApiClient(NotifyAdminAPIClient):
    def sanitise_letter(self, service_id, pdf_file, *, upload_id):
        response = self.post(
            url=f"/service/{service_id}/letter-upload/sanitise",
            data={"file": base64.b64encode(pdf_file).decode("utf-8"), "upload_id": str(upload_id)},
        )
        return SanitisedLetter(response["status_code"], response["data"])

    def get_png_for_invalid_pdf_page(self, service_id, pdf_file, page):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)
        response = self.post(
            url=f"/service/{service_id}/letter-upload/overlay.png",
            data={"file": base64.b64encode(pdf_page).decode("utf-8"), "page_number": int(page)},
        )
        return base64.b64decode(response["png"]), 200, {"Content-Type": "image/png"}


_letter_upload_api_client_context_var: ContextVar[LetterUploadApiClient | None] = ContextVar("letter_upload_api_client")
get_letter_upload_api_client: LazyLocalGetter[LetterUploadApiClient] = LazyLocalGetter(
    _letter_upload_api_client_context_var,
    lambda: LetterUploadApiClient(current_app),
)
memo_resetters.append(lambda: get_letter_upload_api_client.clear())
letter_upload_api_client: LetterUploadApiClient = LocalProxy(get_letter_upload_api_client)  # type: ignore[assignment]
