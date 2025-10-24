import re
from abc import ABC, abstractmethod

from flask import current_app, render_template
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType
from notifications_utils.field import Field
from notifications_utils.formatters import autolink_urls, formatted_list
from notifications_utils.markdown import notify_email_markdown
from notifications_utils.recipient_validation.email_address import validate_email_address
from notifications_utils.recipient_validation.errors import InvalidEmailError, InvalidPhoneError
from notifications_utils.recipient_validation.notifynl.phone_number import PhoneNumber
from notifications_utils.sanitise_text import SanitiseSMS
from ordered_set import OrderedSet
from wtforms import ValidationError
from wtforms.validators import URL, DataRequired, InputRequired, StopValidation
from wtforms.validators import Length as WTFormsLength

from app import antivirus_client, current_service, zendesk_client
from app.formatters import sentence_case
from app.main._commonly_used_passwords import commonly_used_passwords
from app.models.spreadsheet import Spreadsheet
from app.notify_client.protected_sender_id_api_client import protected_sender_id_api_client
from app.utils.user import is_gov_user


class CommonlyUsedPassword:
    def __init__(self, message=None):
        if not message:
            message = "Wachtwoord staat in de lijst veelvoorkomende wachtwoorden."
        self.message = message

    def __call__(self, form, field):
        if field.data in commonly_used_passwords:
            raise ValidationError(self.message)


class CsvFileValidator:
    def __init__(self, message="Geen CSV bestand"):
        self.message = message

    def __call__(self, form, field):
        if not Spreadsheet.can_handle(field.data.filename):
            raise ValidationError("Dit bestand moet een spreadsheet zijn dat Notify kan lezen")


class ValidGovEmail:
    def __call__(self, form, field):
        if field.data == "":
            return

        from flask import url_for

        message = """
            Vul een e-mailadres in van een publieke organisatie of
            <a class="govuk-link govuk-link--no-visited-state" href="{}">ontdek wie NotifyNL kunnen gebruiken</a>
        """.format(url_for("main.guidance_who_can_use_notify"))
        if not is_gov_user(field.data.lower()):
            raise ValidationError(message)


class ValidEmail:
    def __init__(
        self,
        message="Vul een mailadres in het juiste formaat in, zoals naam@voorbeeld.nl",
        error_summary_message="Vul %s in het juiste formaat in",
    ):
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        if not field.data:
            return

        try:
            validate_email_address(field.data)
        except InvalidEmailError as e:
            if hasattr(field, "error_summary_messages"):
                field.error_summary_messages.append(self.error_summary_message)
            raise ValidationError(self.message) from e


class ValidPhoneNumber:
    def __init__(
        self,
        allow_international_sms=False,
        allow_sms_to_uk_landlines=False,
        message=None,
    ):
        self.allow_international_sms = allow_international_sms
        self.allow_sms_to_uk_landlines = allow_sms_to_uk_landlines
        self.message = message

    _error_summary_messages_map = {
        InvalidPhoneError.Codes.TOO_SHORT: "%s is te kort",
        InvalidPhoneError.Codes.TOO_LONG: "%s is te lang",
        InvalidPhoneError.Codes.NOT_A_UK_MOBILE: "%s ziet er niet uit als een Nederlands nummer",
        InvalidPhoneError.Codes.UNSUPPORTED_COUNTRY_CODE: "Landcode voor %s niet gevonden",
        InvalidPhoneError.Codes.UNKNOWN_CHARACTER: "%s kan alleen bevatten: 0 1 2 3 4 5 6 7 8 9 ( ) + -",
        InvalidPhoneError.Codes.INVALID_NUMBER: "%s is niet correct – controleer het telefoonnummer",
    }

    def __call__(self, form, field):
        try:
            if field.data:
                number = PhoneNumber(field.data)
                number.validate(
                    allow_international_number=self.allow_international_sms,
                    allow_uk_landline=self.allow_sms_to_uk_landlines,
                )
        except InvalidPhoneError as e:
            error_message = str(e)
            if hasattr(field, "error_summary_messages"):
                error_summary_message = self._error_summary_messages_map[e.code]

                field.error_summary_messages.append(error_summary_message)

            raise ValidationError(error_message) from e


class NoCommasInPlaceHolders:
    def __init__(self, message="Geen komma's toegestaan tussen dubbele haakjes"):
        self.message = message

    def __call__(self, form, field):
        if "," in "".join(Field(field.data).placeholders):
            raise ValidationError(self.message)


class NoElementInSVG(ABC):
    @property
    @abstractmethod
    def element(self):
        pass

    @property
    @abstractmethod
    def message(self):
        pass

    def __call__(self, form, field):
        svg_contents = field.data.stream.read().decode("utf-8")
        field.data.stream.seek(0)
        if f"<{self.element}" in svg_contents.lower():
            raise ValidationError(self.message)


class NoEmbeddedImagesInSVG(NoElementInSVG):
    element = "image"
    message = "Deze SVG bevat een rasterplaat en zal waarschijnlijk niet mooi weergegeven worden"


class NoTextInSVG(NoElementInSVG):
    element = "text"
    message = "Deze SVG bevat teksten die niet goed geconverteerd en mogelijk niet goed weergegeven kunnen worden"


class OnlySMSCharacters:
    def __init__(self, *args, template_type, **kwargs):
        self._template_type = template_type
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        non_sms_characters = sorted(SanitiseSMS.get_non_compatible_characters(field.data))
        if non_sms_characters:
            raise ValidationError(
                "U kunt geen {} gebruiken in SMS-berichten. {} worden niet goed weergegeven op telefoons.".format(
                    formatted_list(non_sms_characters, conjunction="of", before_each="", after_each=""),
                    ("It" if len(non_sms_characters) == 1 else "Deze karakters"),
                )
            )


class DoesNotStartWithDoubleZero:
    def __init__(self, message="SMS-bericht verstuurders identificatie kan niet beginnen met 00"):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.startswith("00"):
            raise ValidationError(self.message)


class IsNotAGenericSenderID:
    generic_sender_ids = ["info", "verify", "alert"]

    def __init__(
        self,
        message="SMS-bericht verstuurders identificatie mag niet Alert, Info of Verify zijn omdat deze verboden zijn.",
    ):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.lower() in self.generic_sender_ids:
            raise ValidationError(self.message)


class IsNotLikeNHSNoReply:
    def __call__(self, form, field):
        lower_cased_data = field.data.lower()
        if (
            field.data
            and ("nhs" in lower_cased_data and "no" in lower_cased_data and "reply" in lower_cased_data)
            and field.data != "NHSNoReply"
        ):
            raise ValidationError(
                "SMS-bericht verstuurders identificatie moet bij andere ziekenfonds diensten passen. "
                "Verander het in ‘ZiekenfondsNoReply’"
            )


def create_phishing_senderid_zendesk_ticket(senderID=None):
    ticket_message = render_template(
        "support-tickets/phishing-senderid.txt",
        senderID=senderID,
    )
    ticket = NotifySupportTicket(
        subject=f"Mogelijke Phishing verstuurders Identificatie - {current_service.name}",
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_TASK,
        notify_ticket_type=NotifyTicketType.TECHNICAL,
        notify_task_type="notify_task_blocked_sender",
    )
    zendesk_client.send_ticket_to_zendesk(ticket)


class IsNotAPotentiallyMaliciousSenderID:
    def __call__(self, form, field):
        if protected_sender_id_api_client.get_check_sender_id(sender_id=field.data):
            create_phishing_senderid_zendesk_ticket(senderID=field.data)
            current_app.logger.warning(
                "Gebruiker probeerde een verstuurdersidentificatie te veranderen in een mogelijk verdachte waarde: %s",
                field.data,
            )
            raise ValidationError(
                f"SMS-bericht verstuurders identificatie mag geen ‘{field.data}’ zijn - "
                "in verband met risico op phishing"
            )


class IsAUKMobileNumberOrShortCode:
    number_regex = re.compile(r"^[0-9\.]+$")
    mobile_regex = re.compile(r"^07[0-9]{9}$")
    shortcode_regex = re.compile(r"^[6-8][0-9]{4}$")

    def __init__(
        self, message="Een numeriek verstuurdersidentificatie moet een valide mobiel nummer of een korte code zijn"
    ):
        self.message = message

    def __call__(self, form, field):
        if (
            field.data
            and re.match(self.number_regex, field.data)
            and not re.match(self.mobile_regex, field.data)
            and not re.match(self.shortcode_regex, field.data)
        ):
            raise ValidationError(self.message)


class MustContainAlphanumericCharacters:
    regex = re.compile(r".*[a-zA-Z0-9].*[a-zA-Z0-9].*")

    def __init__(self, *, thing=None, message="Moet ten minste twee alfanumerieke karakters bevatten"):
        if thing:
            self.message = f"{sentence_case(thing)} moet ten minste 2 letters of cijfers bevatten"
        else:
            # DEPRECATED - prefer to pass in `thing` instead. When all instances are using `thing,` retire `message`
            # altogether.
            self.message = message

    def __call__(self, form, field):
        if field.data and not re.match(self.regex, field.data):
            raise ValidationError(self.message)


class CharactersNotAllowed:
    def __init__(self, characters_not_allowed, *args, thing="item", message=None, error_summary_message=None):
        self.characters_not_allowed = OrderedSet(characters_not_allowed)
        self.thing = thing
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        illegal_characters = self.characters_not_allowed.intersection(field.data)

        if illegal_characters:
            if self.message:
                error_message = self.message
            else:
                error_message = (
                    f"Mag niet bevatten "
                    f"{formatted_list(illegal_characters, conjunction='or', before_each='', after_each='')}"
                )

            if hasattr(field, "error_summary_messages"):
                if self.error_summary_message:
                    error_summary_message = self.error_summary_message
                else:
                    error_summary_message = (
                        f"%s mag niet bevatten "
                        f"{formatted_list(illegal_characters, conjunction='or', before_each='', after_each='')}"
                    )
                field.error_summary_messages.append(error_summary_message)

            raise ValidationError(error_message)


class StringsNotAllowed:
    def __init__(self, *args, thing="item", message=None, error_summary_message=None, match_on_substrings=False):
        self.strings_not_allowed = OrderedSet(string.lower() for string in args)
        self.match_on_substrings = match_on_substrings
        self.thing = thing
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        normalised = field.data.lower()
        for not_allowed in self.strings_not_allowed:
            if normalised == not_allowed or (self.match_on_substrings and not_allowed in normalised):
                if self.message:
                    error_message = self.message
                else:
                    error_message = f"Mag niet {'bevatten' if self.match_on_substrings else 'zijn'} ‘{not_allowed}’"

                if hasattr(field, "error_summary_messages"):
                    if self.error_summary_message:
                        error_summary_message = self.error_summary_message
                    else:
                        error_summary_message = (
                            f"%s mag niet {'bevatten' if self.match_on_substrings else 'zijn'} ‘{not_allowed}’"
                        )
                    field.error_summary_messages.append(error_summary_message)

                raise ValidationError(error_message)


class FileIsVirusFree:
    def __call__(self, form, field):
        if field.data:
            if current_app.config["ANTIVIRUS_ENABLED"]:
                try:
                    virus_free = antivirus_client.scan(field.data)
                    if not virus_free:
                        raise StopValidation("Dit bestand bevat een virus")
                finally:
                    field.data.seek(0)


class NotifyDataRequired(DataRequired):
    def __init__(self, thing):
        super().__init__(message=f"Vul {thing} in")


class NotifyInputRequired(InputRequired):
    def __init__(self, thing):
        super().__init__(message=f"Vul {thing} in")


class NotifyUrlValidator(URL):
    def __init__(self, thing="een URL in het correcte formaat"):
        super().__init__(message=f"Vul {thing} in")


class CannotContainURLsOrLinks:
    def __init__(self, *, thing):
        self.thing = thing

    def __call__(self, form, field):
        for func in (autolink_urls, notify_email_markdown):
            if "<a href=" in func(field.data):
                raise ValidationError(f"{self.thing.capitalize()} mag geen URL bevatten")


class Length(WTFormsLength):
    def __init__(self, min=-1, max=-1, message=None, thing=None, unit="karakters"):
        super().__init__(min=min, max=max, message=message)
        self.thing = thing
        self.unit = unit

        if not self.message:
            if not self.thing:
                raise RuntimeError("Moet `thing` aanleveren (voorkeur) tenzij `message` expliciet ingevuld is.")

            if min >= 0 and max >= 0:
                if min == max:
                    self.message = f"{sentence_case(thing)} moet {min} {unit} lang zijn"
                else:
                    self.message = f"{sentence_case(thing)} moet tussen {min} en {max} {unit} lang zijn"
            elif min >= 0:
                self.message = f"{sentence_case(thing)} must ten minste {min} {unit} lang zijn"
            else:
                self.message = f"{sentence_case(thing)} mag niet langer zijn dan {max} {unit}"
