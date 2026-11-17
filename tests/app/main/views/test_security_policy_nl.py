from datetime import UTC, datetime

from app.main.views_nl.security_policy import SECURITY_TXT_EXPIRES


def test_security_txt_is_served_as_plain_text(client_request, notify_admin):
    client_request.logout()
    response = client_request.get_response("main.security_policy")

    assert response.content_type == "text/plain; charset=utf-8"
    lines = response.get_data(as_text=True).splitlines()
    assert lines == [
        "Contact: mailto:info@worth.nl",
        f"Expires: {SECURITY_TXT_EXPIRES}",
        "Preferred-Languages: en, nl",
        "Policy: https://github.com/Worth-NL/notifynl-admin/security/policy",
        f"Canonical: {notify_admin.config['ADMIN_BASE_URL']}/.well-known/security.txt",
    ]


def test_security_txt_does_not_point_to_the_uk(client_request):
    client_request.logout()
    response = client_request.get_response("main.security_policy")

    assert "gov.uk" not in response.get_data(as_text=True)


def test_security_txt_expiry_is_in_the_future():
    expires = datetime.strptime(SECURITY_TXT_EXPIRES, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)

    assert expires > datetime.now(UTC)


def test_legacy_security_txt_redirects_to_well_known(client_request):
    client_request.logout()
    client_request.get_url(
        "/security.txt",
        _expected_status=301,
        _expected_redirect="/.well-known/security.txt",
    )
