"""Separate session gate for the Manage Users admin area."""

SESSION_KEY = "user_manage_verified"
USER_MANAGE_PATH_PREFIX = "/accounts/users"


def is_user_manage_verified(request) -> bool:
    return bool(request.session.get(SESSION_KEY))


def set_user_manage_verified(request) -> None:
    request.session[SESSION_KEY] = True


def clear_user_manage_verified(request) -> None:
    request.session.pop(SESSION_KEY, None)
