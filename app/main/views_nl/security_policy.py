from flask import Response, current_app, redirect, url_for

from app.main import main

# RFC 9116 security.txt, based on the repository's SECURITY.md.
# Expires must be renewed before it passes (RFC 9116 advises less than a year ahead).
SECURITY_TXT_EXPIRES = "2027-10-08T00:00:00Z"


@main.route("/.well-known/security.txt", methods=["GET"])
def security_policy():
    canonical = f"{current_app.config['ADMIN_BASE_URL']}/.well-known/security.txt"
    return Response(
        "\n".join(
            [
                "Contact: mailto:info@worth.nl",
                f"Expires: {SECURITY_TXT_EXPIRES}",
                "Preferred-Languages: en, nl",
                "Policy: https://github.com/Worth-NL/notifynl-admin/security/policy",
                f"Canonical: {canonical}",
                "",
            ]
        ),
        mimetype="text/plain",
    )


@main.route("/security.txt", methods=["GET"])
def security_policy_legacy():
    return redirect(url_for("main.security_policy"), 301)
