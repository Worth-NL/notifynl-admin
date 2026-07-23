from datetime import UTC, datetime, timedelta

from dateutil import parser
from flask import url_for
from notifications_utils.formatters import unescaped_formatted_list
from notifications_utils.letter_timings import letter_can_be_cancelled
from notifications_utils.recipient_validation.notifynl.postal_address import PostalAddress
from notifications_utils.template import BaseLetterTemplate
from notifications_utils.timezones import (
    local_timezone,
    utc_string_to_aware_gmt_datetime,
)

from app.overrides_nl.formatters import _format_datetime_short


def printing_today_or_tomorrow(created_at):
    print_cutoff = datetime.now(local_timezone).replace(hour=17, minute=30)
    created_at = utc_string_to_aware_gmt_datetime(created_at)

    if created_at < print_cutoff:
        return "vandaag"
    else:
        return "morgen"


def get_letter_printing_statement(status, created_at, long_form=True):
    if isinstance(created_at, datetime):
        created_at = created_at.astimezone(UTC).isoformat()
    created_at_dt = parser.parse(created_at).replace(tzinfo=None)
    if letter_can_be_cancelled(status, created_at_dt):
        description = "Het printen start" if long_form else "Printen"
        return f"{description} {printing_today_or_tomorrow(created_at)} om 17:30 uur"
    else:
        printed_datetime = utc_string_to_aware_gmt_datetime(created_at) + timedelta(hours=6, minutes=30)
        if printed_datetime.date() == datetime.now().date():
            return "Geprint vandaag om 17:30 uur"
        elif printed_datetime.date() == datetime.now().date() - timedelta(days=1):
            return "Geprint gisteren om 17:30 uur"

        printed_date = _format_datetime_short(printed_datetime)
        description = "Geprint op" if long_form else "Geprint"

        return f"{description} {printed_date} om 17:30 uur"


LETTER_VALIDATION_MESSAGES = {
    "letter-not-a4-portrait-oriented": {
        "title": "Uw brief heeft niet het formaat A4 staand",
        "detail": (
            "U moet het formaat of de richting van {invalid_pages} wijzigen. <br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}" target="_blank">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
        "summary": (
            "De validatie is mislukt omdat {invalid_pages} niet het formaat A4 staand {invalid_pages_are_or_is}.<br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
    },
    "content-outside-printable-area": {
        "title": "Uw inhoud valt buiten het afdrukbare gebied",
        "detail": (
            "U moet {invalid_pages} bewerken.<br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
        "summary": (
            "De validatie is mislukt omdat de inhoud buiten het afdrukbare gebied valt op {invalid_pages}.<br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}" target="_blank">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
    },
    "letter-too-long": {
        "title": "Uw brief is te lang",
        "detail": (
            f"Brieven mogen maximaal {BaseLetterTemplate.max_page_count} pagina’s bevatten "
            f"({BaseLetterTemplate.max_sheet_count} dubbelzijdige vellen papier). <br>"
            "Uw brief is {page_count} pagina’s lang."
        ),
        "summary": (
            "De validatie is mislukt omdat deze brief {page_count} pagina’s lang is.<br>"
            f"Brieven mogen maximaal {BaseLetterTemplate.max_page_count} pagina’s bevatten "
            f"({BaseLetterTemplate.max_sheet_count} dubbelzijdige vellen papier)."
        ),
    },
    "no-encoded-string": {"title": "Opschonen mislukt - geen gecodeerde tekenreeks"},
    "unable-to-read-the-file": {
        "title": "Er is een probleem met uw bestand",
        "detail": (
            "NotifyNL kan deze PDF niet lezen.<br>Sla een nieuwe kopie van uw bestand op en probeer het opnieuw."
        ),
        "summary": (
            "De validatie is mislukt omdat NotifyNL deze PDF niet kan lezen.<br>"
            "Sla een nieuwe kopie van uw bestand op en probeer het opnieuw."
        ),
    },
    "address-is-empty": {
        "title": "Het adresblok is leeg",
        "detail": (
            "U moet een adres van de ontvanger toevoegen.<br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}" target="_blank">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
        "summary": (
            "De validatie is mislukt omdat het adresblok leeg is.<br>"
            "Bestanden moeten voldoen aan onze "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}" target="_blank">'
            "briefspecificatie (opent in een nieuw tabblad)"
            "</a>."
        ),
    },
    "not-a-real-uk-postcode": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "De laatste regel van het adres moet een geldige postcode uit het VK zijn.",
        "summary": "De validatie is mislukt omdat de laatste regel van het adres geen geldige postcode uit het VK is.",
    },
    "cant-send-international-letters": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "U heeft geen toestemming om brieven naar andere landen te versturen.",
        "summary": "De validatie is mislukt omdat uw dienst geen brieven naar andere landen kan versturen.",
    },
    "not-a-real-uk-postcode-or-country": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "De laatste regel van het adres moet een postcode uit het VK of een ander land zijn.",
        "summary": (
            "De validatie is mislukt omdat de laatste regel van het adres geen postcode uit het VK "
            "of een ander land is."
        ),
    },
    "not-enough-address-lines": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": f"Het adres moet minstens {PostalAddress.MIN_LINES} regels lang zijn.",
        "summary": (
            f"De validatie is mislukt omdat het adres minstens {PostalAddress.MIN_LINES} regels lang moet zijn."
        ),
    },
    "too-many-address-lines": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": f"Het adres mag maximaal {PostalAddress.MAX_LINES} regels bevatten.",
        "summary": (f"De validatie is mislukt omdat het adres maximaal {PostalAddress.MAX_LINES} regels mag bevatten."),
    },
    "invalid-char-in-address": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "Adresregels mogen niet beginnen met een van de volgende tekens: @ ( ) = [ ] ” \\ / , < > ~",
        "summary": (
            "De validatie is mislukt omdat adresregels niet mogen beginnen met een van de "
            "volgende tekens: @ ( ) = [ ] ” \\ / , < > ~"
        ),
    },
    "has-country-for-bfpo-address": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "De laatste regel van een BFPO-adres mag geen land zijn.",
        "summary": "De validatie is mislukt omdat de laatste regel van het BFPO-adres een land is.",
    },
    "notify-tag-found-in-content": {
        "title": "Er is een probleem met uw brief",
        "detail": "Uw bestand bevat een brief die u heeft gedownload van NotifyNL.<br>U moet {invalid_pages} bewerken.",
        "summary": (
            "De validatie is mislukt omdat uw bestand een brief bevat die u heeft gedownload "
            "van NotifyNL op {invalid_pages}."
        ),
    },
    "no-fixed-abode-address": {
        "title": "Er is een probleem",
        "detail": "Voer een geldig adres in.",
        "summary": "De validatie is mislukt omdat dit geen geldig adres is.",
    },
    "invalid-address-line-1-or-2": {
        "title": "Er is een probleem met het adres voor deze brief",
        "detail": "De eerste 2 regels moeten beide minstens één alfanumeriek teken bevatten.",
        "summary": ("De validatie is mislukt omdat regel 1 en 2 van het adres geen alfanumeriek teken bevatten."),
    },
}


def get_letter_validation_error(validation_message, invalid_pages=None, page_count=None):
    if not invalid_pages:
        invalid_pages = []
    if validation_message not in LETTER_VALIDATION_MESSAGES:
        return {"title": "Validatie mislukt"}

    invalid_pages_are_or_is = "is" if len(invalid_pages) == 1 else "zijn"

    invalid_pages = unescaped_formatted_list(
        invalid_pages, before_each="", after_each="", prefix="pagina", prefix_plural="pagina’s", conjunction="en"
    )

    return {
        "title": LETTER_VALIDATION_MESSAGES[validation_message]["title"],
        "detail": LETTER_VALIDATION_MESSAGES[validation_message]["detail"].format(
            invalid_pages=invalid_pages,
            invalid_pages_are_or_is=invalid_pages_are_or_is,
            page_count=page_count,
            letter_spec_guidance=url_for("main.guidance_upload_a_letter"),
        ),
        "summary": LETTER_VALIDATION_MESSAGES[validation_message]["summary"].format(
            invalid_pages=invalid_pages,
            invalid_pages_are_or_is=invalid_pages_are_or_is,
            page_count=page_count,
            letter_spec_guidance=url_for("main.guidance_upload_a_letter"),
        ),
    }


def get_error_from_upload_form(form_errors):
    error = {}
    if "PDF" in form_errors:
        error["title"] = "Verkeerd bestandstype"
    else:
        error["title"] = "Er is een probleem"

    error["detail"] = form_errors

    return error
