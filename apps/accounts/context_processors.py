from .social import get_social_login_providers


def social_login_providers(request):
    return {"social_login_providers": get_social_login_providers()}
