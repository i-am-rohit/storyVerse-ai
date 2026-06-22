from .user_manage_session import USER_MANAGE_PATH_PREFIX, clear_user_manage_verified


class UserManageSessionMiddleware:
    """Clear Manage Users access when the user leaves the admin area."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(USER_MANAGE_PATH_PREFIX):
            clear_user_manage_verified(request)
        return self.get_response(request)
