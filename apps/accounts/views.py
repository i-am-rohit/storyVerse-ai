from allauth.account.internal.flows.logout import logout as account_logout
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView

from .forms import UserRegistrationForm
from .models import Profile
from .user_manage_session import clear_user_manage_verified, set_user_manage_verified


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(None)
        return response


class UserManageLoginView(LoginView):
    """Separate superuser login for the user management area."""

    template_name = "accounts/user_login.html"
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET":
            clear_user_manage_verified(request)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("accounts:user_manage")

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.user.is_superuser:
            logout(self.request)
            clear_user_manage_verified(self.request)
            messages.error(
                self.request,
                "Only superuser accounts can access Manage Users.",
            )
            return redirect("accounts:user_login")
        set_user_manage_verified(self.request)
        self.request.session.set_expiry(None)
        messages.success(self.request, "Welcome to Manage Users.")
        return response


@require_http_methods(["GET", "POST"])
def logout_user(request):
    clear_user_manage_verified(request)
    if request.user.is_authenticated:
        account_logout(request, show_message=False)
        messages.success(request, "You have been signed out.")
    return redirect("accounts:login")


class UserRegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("stories:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        Profile.objects.get_or_create(user=self.object)
        login(self.request, self.object)
        self.request.session.set_expiry(None)
        return response


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "accounts/profile.html", {"profile": profile_obj})
