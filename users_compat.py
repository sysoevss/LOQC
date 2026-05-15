import os
import threading
from urllib.parse import quote


class User:
    def __init__(self, email):
        self._email = email

    def email(self):
        return self._email

    def nickname(self):
        if not self._email:
            return ""
        return self._email.split("@", 1)[0]

    def __str__(self):
        return self._email


def _extract_email(raw_value):
    if not raw_value:
        return None
    value = raw_value.strip()
    if ":" in value:
        _, value = value.split(":", 1)
    return value or None


_thread_context = threading.local()


def set_request_environ(environ):
    _thread_context.environ = environ


def clear_request_environ():
    _thread_context.environ = None


def _get_environ():
    environ = getattr(_thread_context, "environ", None)
    return environ or os.environ


def get_current_user():
    # IAP header (recommended for App Engine Python 3)
    environ = _get_environ()
    email = _extract_email(environ.get("HTTP_X_GOOG_AUTHENTICATED_USER_EMAIL"))
    if not email:
        # Legacy header used in older runtimes
        email = _extract_email(environ.get("HTTP_X_APPENGINE_USER_EMAIL"))
    if not email:
        return None
    return User(email)


def create_login_url(dest_url="/my"):
    # IAP signs users in at the load balancer. Use /my (or continue target) in the UI;
    # this URL shows an in-app help page if the IAP header is still missing.
    target = dest_url or "/my"
    return "/login?continue=" + quote(target)


def create_logout_url(dest_url="/"):
    # IAP logout is handled externally; redirect back.
    return dest_url or "/"
