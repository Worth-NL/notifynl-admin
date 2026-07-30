import re
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, flash, redirect, request, session, url_for

from app.models.user import User


def redirect_to_sign_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_details" not in session:
            return redirect(url_for("main.sign_in"))
        else:
            return f(*args, **kwargs)

    return wrapped


def log_in_user(user_id):
    try:
        user = User.from_id(user_id)
        # the user will have a new current_session_id set by the API - store it in the cookie for future requests
        session["current_session_id"] = user.current_session_id
        # Check if coming from new password page
        if "new_password" in session.get("user_details", {}):
            try:
                user.update_password(decrypt_new_password(session["user_details"]["new_password"]))
            except InvalidToken:
                current_app.logger.warning(
                    "Error during new password decryption for user id %s",
                    user_id,
                )
                flash("There was a problem with your password. Please try again.")
                return redirect(url_for("main.sign_in"))

        user.activate()
        user.login()
    finally:
        # get rid of anything in the session that we don't expect to have been set during register/sign in flow
        session.pop("user_details", None)
        session.pop("file_uploads", None)

    return redirect_when_logged_in()


def redirect_when_logged_in():
    next_url = request.args.get("next")
    if next_url and is_safe_redirect_url(next_url):
        # is_safe_redirect_url enforces a strict same-origin allowlist (single leading
        # slash, no backslashes, no protocol-relative //) - see commit 55f54c0d9 for the
        # browser-parsing edge cases it closes. CodeQL's taint tracking doesn't see across
        # this custom sanitizer, hence the inline suppression below.
        return redirect(next_url)  # codeql[py/url-redirection]

    return redirect(url_for("main.show_accounts_or_dashboard"))


def redirect_if_logged_in(f):
    from app import current_user

    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user and current_user.is_authenticated:
            return redirect_when_logged_in()
        else:
            return f(*args, **kwargs)

    return wrapped


def is_safe_redirect_url(target):
    # Only allow same-origin relative paths. A urljoin/urlparse-based
    # netloc comparison isn't enough here: browsers treat backslashes the
    # same as forward slashes, and treat any run of 2+ leading slashes as an
    # absolute/protocol-relative URL - including same-scheme-prefixed forms
    # like "https:///evil.com" - none of which Python's urllib parses the
    # same way, so a value that looks same-origin to urlparse can still send
    # a real browser to an external host. Rather than replicate every quirky
    # absolute-URL form a browser might recognise, only allow the one
    # unambiguously-safe shape: a path starting with exactly one slash.
    #
    # Browsers also strip ASCII tab/CR/LF from a URL wherever they occur
    # before parsing it (WHATWG URL spec), including from a redirect's
    # Location header - so e.g. "/\t/evil.com" looks like a single safe
    # leading slash here, but collapses to "//evil.com" (protocol-relative)
    # by the time the browser navigates to it. Strip those characters first
    # so the check sees what the browser will actually see.
    if not target:
        return False
    stripped = re.sub(r"[\t\r\n]", "", target)
    normalised = stripped.replace("\\", "/")
    return normalised.startswith("/") and not normalised.startswith("//")


def encrypt_new_password(new_password: str) -> bytes:
    fernet = Fernet(current_app.config["NEW_PASSWORD_ENCRYPTION_KEY"].encode("utf-8"))
    return fernet.encrypt(new_password.encode(encoding="utf-8"))


def decrypt_new_password(new_password: bytes) -> str:
    fernet = Fernet(current_app.config["NEW_PASSWORD_ENCRYPTION_KEY"].encode("utf-8"))
    return fernet.decrypt(new_password).decode(encoding="utf-8")
