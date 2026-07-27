from flask import abort
from notifications_utils.base64_uuid import base64_to_uuid, uuid_to_base64
from werkzeug.routing import BaseConverter, ValidationError

from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from app.models.service import Service


class AgreementTypeConverter(BaseConverter):
    regex = "(?:crown|non-crown)"


class TemplateTypeConverter(BaseConverter):
    regex = f"(?:{'|'.join(Service.TEMPLATE_TYPES)})"


class BrandingTypeConverter(BaseConverter):
    regex = "(?:email|letter)"


class DailyLimitTypeConverter(BaseConverter):
    # messagebox isn't in Service.TEMPLATE_TYPES: that also drives the "create template" type
    # picker and nav tabs, which don't support messagebox yet, so it's added here directly.
    regex = f"(?:{'|'.join(Service.TEMPLATE_TYPES)}|international_sms|messagebox)"


class NotificationTypeConverter(BaseConverter):
    # Deliberately separate from TemplateTypeConverter (same reasoning as
    # DailyLimitTypeConverter above): messagebox notifications exist and need to be
    # filterable/listable, but messagebox isn't in Service.TEMPLATE_TYPES, and the
    # template create/edit routes that share TemplateTypeConverter aren't built to
    # handle it.
    regex = f"(?:{'|'.join(Service.TEMPLATE_TYPES)}|messagebox)"


class TicketTypeConverter(BaseConverter):
    regex = f"(?:{PROBLEM_TICKET_TYPE}|{QUESTION_TICKET_TYPE})"


class LetterFileExtensionConverter(BaseConverter):
    regex = "(?:pdf|png)"


class SimpleDateTypeConverter(BaseConverter):
    regex = r"([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))"


class Base64UUIDConverter(BaseConverter):
    def to_python(self, value):
        try:
            return base64_to_uuid(value)
        except ValueError as e:
            raise ValidationError from e

    def to_url(self, value):
        try:
            return uuid_to_base64(value)
        except Exception as e:
            raise ValidationError from e


def base64_to_uuid_or_404(value):
    try:
        return base64_to_uuid(value or "")
    except ValueError:
        abort(404)
