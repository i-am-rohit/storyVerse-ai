from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import superuser_required
from .forms import AdminPasswordResetForm, AdminUserCreateForm
from .models import Profile


def _user_queryset():
    return (
        User.objects.annotate(
            story_count=Count("stories", distinct=True),
            audiobook_count=Count("audiobooks", distinct=True),
        )
        .order_by("-date_joined")
    )


@superuser_required
def user_manage(request):
    users = list(_user_queryset())
    return render(request, "accounts/user_manage.html", {
        "users": users,
        "create_form": AdminUserCreateForm(),
        "total_users": len(users),
    })


@superuser_required
@require_POST
def user_create(request):
    form = AdminUserCreateForm(request.POST)
    if form.is_valid():
        user = form.save()
        Profile.objects.get_or_create(user=user)
        messages.success(request, f'User "{user.username}" created successfully.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                label = field if field == "__all__" else form.fields.get(field, field).label
                messages.error(request, f"{label}: {error}")
    return redirect("accounts:user_manage")


@superuser_required
@require_POST
def user_reset_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    form = AdminPasswordResetForm(request.POST, prefix=f"reset-{user_id}")
    if form.is_valid():
        target.set_password(form.cleaned_data["password1"])
        target.save()
        messages.success(request, f'Password reset for "{target.username}".')
    else:
        for error in form.errors.values():
            messages.error(request, error[0])
    return redirect("accounts:user_manage")


@superuser_required
@require_POST
def user_delete(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account while logged in.")
        return redirect("accounts:user_manage")

    if target.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, "Cannot delete the only superuser account.")
        return redirect("accounts:user_manage")

    username = target.username
    target.delete()
    messages.success(request, f'User "{username}" deleted.')
    return redirect("accounts:user_manage")
