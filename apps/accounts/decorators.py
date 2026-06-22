from functools import wraps

from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

from .user_manage_session import is_user_manage_verified


def superuser_required(view_func):
    """Allow access only after a fresh Manage Users login."""

    @login_required(login_url=reverse_lazy("accounts:user_login"))
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from django.contrib import messages
        from django.shortcuts import redirect

        if not request.user.is_superuser:
            messages.error(request, "Superuser login required to manage users.")
            return redirect("accounts:user_login")
        if not is_user_manage_verified(request):
            messages.info(request, "Please sign in to Manage Users.")
            return redirect("accounts:user_login")
        return view_func(request, *args, **kwargs)

    return wrapper
