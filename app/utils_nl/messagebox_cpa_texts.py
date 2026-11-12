"""
[NotifyNL] Dutch for the CPA checks, warnings and refusals that notifynl-api returns in English
(app/messagebox/cpa_nl.py there). A text that matches no pattern, e.g. after the API's wording changes, is shown as
the API sent it.
"""

import re

_PATTERNS = [
    # checks
    (r"ebms-core accepts the CPA", "ebms-core accepteert de CPA"),
    (r"ebms-core rejects the CPA: (?P<reason>.*)", "ebms-core weigert de CPA: {reason}"),
    (r"The CPA has 2 parties", "De CPA heeft 2 partijen"),
    (r"The CPA has (?P<count>\d+) parties instead of 2", "De CPA heeft {count} partijen in plaats van 2"),
    (
        r"EBMS_PUBLIC_ENDPOINT isn't configured for this environment",
        "EBMS_PUBLIC_ENDPOINT is niet ingesteld voor deze omgeving",
    ),
    (
        r"Exactly one party must have our endpoint (?P<endpoint>\S+)",
        "Precies één partij moet ons endpoint {endpoint} hebben",
    ),
    (
        r"Our party also lists other endpoints than (?P<endpoint>\S+)",
        "Onze partij heeft ook andere endpoints dan {endpoint}",
    ),
    (r"Our endpoint is (?P<endpoint>\S+)", "Ons endpoint is {endpoint}"),
    (r"The other party couldn't be determined", "De andere partij kan niet worden bepaald"),
    (r"The other party has no valid endpoint", "De andere partij heeft geen geldig endpoint"),
    (r"(?P<endpoints>.+) doesn't use https", "{endpoints} gebruikt geen https"),
    (
        r"(?P<hosts>.+) isn't allowed for (?P<purpose>\w+) \(allowed: none\)",
        "{hosts} is niet toegestaan voor {purpose} (toegestaan: geen)",
    ),
    (
        r"(?P<hosts>.+) isn't allowed for (?P<purpose>\w+) \(allowed: (?P<allowed>.*)\)",
        "{hosts} is niet toegestaan voor {purpose} (toegestaan: {allowed})",
    ),
    (r"(?P<hosts>.+) is allowed for (?P<purpose>\w+)", "{hosts} is toegestaan voor {purpose}"),
    (
        r"Our party can't send (?P<action>\S+) as (?P<role>\S+) in process (?P<process>\S+)",
        "Onze partij kan {action} niet versturen als {role} in proces {process}",
    ),
    (
        r"The other party can't receive (?P<action>\S+) as (?P<role>\S+) in process (?P<process>\S+)",
        "De andere partij kan {action} niet ontvangen als {role} in proces {process}",
    ),
    (
        r"Our party sends (?P<action>\S+) as (?P<sender>\S+) to (?P<receiver>\S+) \((?P<process>[^)]+)\)",
        "Onze partij verstuurt {action} als {sender} naar {receiver} ({process})",
    ),
    (r"The CPA is only proposed, not agreed", "De CPA is alleen voorgesteld (proposed), niet overeengekomen (agreed)"),
    (r"The CPA's status is not set", "De CPA heeft geen status"),
    (r"The CPA's status is (?P<status>.+)", "De status van de CPA is {status}"),
    (r"Start isn't before End: from (?P<start>\S+) to (?P<end>\S+)", "Start ligt niet vóór End: van {start} tot {end}"),
    (r"Ended: valid from (?P<start>\S+) to (?P<end>\S+)", "Verlopen: geldig van {start} tot {end}"),
    (r"Not started yet: valid from (?P<start>\S+) to (?P<end>\S+)", "Nog niet begonnen: geldig van {start} tot {end}"),
    (
        r"Valid from (?P<start>\S+) to (?P<end>\S+); it can be selected from (?P<selectable>\S+)",
        "Geldig van {start} tot {end}; te kiezen vanaf {selectable}",
    ),
    (r"Valid from (?P<start>\S+) to (?P<end>\S+)", "Geldig van {start} tot {end}"),
    # warnings
    (r"The CPA ends on (?P<date>\S+)", "De CPA loopt af op {date}"),
    (
        r"Certificate (?P<cert_id>.+) of (?P<party>.+) expires on (?P<date>\S+)",
        "Certificaat {cert_id} van {party} verloopt op {date}",
    ),
    # refusals and listing errors
    (r"The CPA can't be used for (?P<purpose>\w+)", "De CPA kan niet worden gebruikt voor {purpose}"),
    (r"ebms-core already has a CPA with id (?P<cpa_id>.+)", "ebms-core heeft al een CPA met id {cpa_id}"),
    (r"ebms-core has no CPA with id (?P<cpa_id>.+)", "ebms-core heeft geen CPA met id {cpa_id}"),
    (r"ebms-core can't return the CPA: (?P<reason>.*)", "ebms-core kan de CPA niet teruggeven: {reason}"),
]
_COMPILED = [(re.compile(pattern, re.DOTALL), dutch) for pattern, dutch in _PATTERNS]


def dutch_cpa_text(text):
    if not text:
        return text
    for pattern, dutch in _COMPILED:
        if match := pattern.fullmatch(text):
            return dutch.format(**match.groupdict())
    return text


def dutch_assessment(assessment):
    """A copy of notifynl-api's serialised assessment with its check messages and warnings in Dutch."""
    if not assessment:
        return assessment
    return {
        **assessment,
        "checks": [{**check, "message": dutch_cpa_text(check["message"])} for check in assessment.get("checks", [])],
        "warnings": [dutch_cpa_text(warning) for warning in assessment.get("warnings", [])],
    }


def dutch_listing(listing):
    """A copy of a CPA listing from notifynl-api with its error and every assessment in Dutch."""
    return {
        **listing,
        "error": dutch_cpa_text(listing.get("error")),
        "assessments": {
            purpose: dutch_assessment(assessment) for purpose, assessment in (listing.get("assessments") or {}).items()
        },
    }
