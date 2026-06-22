from django.urls import path

from . import admin_views, views

app_name = "accounts"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("register/", views.UserRegisterView.as_view(), name="register"),
    path("profile/", views.profile, name="profile"),
    path("users/login/", views.UserManageLoginView.as_view(), name="user_login"),
    path("users/", admin_views.user_manage, name="user_manage"),
    path("users/create/", admin_views.user_create, name="user_create"),
    path("users/<int:user_id>/reset-password/", admin_views.user_reset_password, name="user_reset_password"),
    path("users/<int:user_id>/delete/", admin_views.user_delete, name="user_delete"),
]
