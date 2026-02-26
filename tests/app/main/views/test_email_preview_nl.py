import pytest


def test_displays_govuk_branding_by_default(client_request):
    page = client_request.get("main.email_template", _test_page_title=False)

    assert page.select_one("a")["href"] == "https://admin.notifynl.nl"


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"branding_style": None},
        {"branding_style": "govuk"},
        {"branding_style": "__NONE__"},
        {"branding_style": ""},
    ],
)
def test_displays_govuk_branding(client_request, params):
    page = client_request.get("main.email_template", **params, _test_page_title=False)
    assert page.select_one("a")["href"] == "https://admin.notifynl.nl"


def test_displays_both_branding(client_request, mock_get_email_branding_with_both_brand_type):
    page = client_request.get("main.email_template", branding_style="1", _test_page_title=False)

    mock_get_email_branding_with_both_brand_type.assert_called_once_with("1")

    assert page.select_one("a")["href"] == "https://www.rijksoverheid.nl/"
    assert page.select("svg")[0]["id"] == "rijksoverheid_logo"
    assert page.select("img")[0]["src"] == "https://static-logos.test.com/example.png"
    assert (
        page.select("body > table:nth-of-type(2) table:nth-of-type(1) table td:nth-of-type(2)")[0].get_text().strip()
        == "Organisation text"
    )  # brand text is set
