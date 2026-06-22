from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Profile


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        Profile.objects.get_or_create(user=user)
        request.session.set_expiry(None)
        return user
