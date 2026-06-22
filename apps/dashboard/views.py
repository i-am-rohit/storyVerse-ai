from django.shortcuts import redirect, render


def home(request):
    """App entry: login if guest, stories library if signed in."""
    if request.user.is_authenticated:
        return redirect("stories:index")
    return redirect("accounts:login")


def landing(request):
    return render(request, "index.html")


def user_guide(request):
    return render(request, "help/user_guide.html")


def index(request):
    """Legacy URL — send users to the main app."""
    return redirect("stories:index")
