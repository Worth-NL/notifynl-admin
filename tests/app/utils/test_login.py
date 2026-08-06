import pytest
from freezegun import freeze_time

from app.models.user import User
from app.utils.login import is_safe_redirect_url


@pytest.mark.parametrize(
    "target",
    (
        "/dashboard",
        "/services/123/dashboard?x=1",
    ),
)
def test_is_safe_redirect_url_allows_same_origin_relative_paths(target):
    assert is_safe_redirect_url(target) is True


@pytest.mark.parametrize(
    "target",
    (
        None,
        "",
        "dashboard",  # no leading slash
        "//evil.com",
        "///evil.com",
        "/\\evil.com",  # browsers treat \ the same as / when resolving a URL
        "\\/evil.com",
        "\\\\evil.com",
        "https://evil.com",
        "https:///evil.com",
        "  //evil.com",
        "https://admin.notifynl.nl@evil.com/",
        "/\t/evil.com",  # browsers strip ASCII tab before parsing, collapsing this to //evil.com
        "/\n/evil.com",  # same, for newline
        "/\r/evil.com",  # same, for carriage return
        "/\t\\evil.com",  # tab-stripping and backslash-normalisation can combine
    ),
)
def test_is_safe_redirect_url_rejects_cross_origin_or_malformed_targets(target):
    assert is_safe_redirect_url(target) is False


@freeze_time("2020-11-27T12:00:00")
@pytest.mark.parametrize(
    ("email_access_validated_at", "expected_result"),
    (
        ("2020-10-01T11:35:21.726132Z", False),
        ("2020-07-23T11:35:21.726132Z", True),
    ),
)
def test_email_needs_revalidating(
    api_user_active,
    email_access_validated_at,
    expected_result,
):
    api_user_active["email_access_validated_at"] = email_access_validated_at
    assert User(api_user_active).email_needs_revalidating == expected_result
