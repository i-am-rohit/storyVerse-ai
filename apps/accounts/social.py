from django.conf import settings
from django.urls import NoReverseMatch, reverse


SOCIAL_PROVIDERS = (
    {
        "id": "google",
        "label": "Gmail",
        "icon": "google",
        "client_id_env": "GOOGLE_OAUTH_CLIENT_ID",
    },
    {
        "id": "microsoft",
        "label": "Outlook",
        "icon": "microsoft",
        "client_id_env": "MICROSOFT_OAUTH_CLIENT_ID",
    },
    {
        "id": "facebook",
        "label": "Facebook",
        "icon": "facebook",
        "client_id_env": "FACEBOOK_OAUTH_CLIENT_ID",
    },
)


def get_social_login_providers():
    providers = []
    for provider in SOCIAL_PROVIDERS:
        try:
            login_url = reverse(f"{provider['id']}_login")
        except NoReverseMatch:
            login_url = f"/oauth/{provider['id']}/login/"

        providers.append({
            **provider,
            "enabled": provider["id"] in settings.SOCIALACCOUNT_PROVIDERS,
            "login_url": login_url,
        })
    return providers


def get_enabled_social_login_providers():
    return [provider for provider in get_social_login_providers() if provider["enabled"]]
