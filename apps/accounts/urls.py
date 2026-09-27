"""Account routes.

Login/logout are Django's stock local views, but they live *here* so they
inherit the ``accounts:`` namespace that ``settings.LOGIN_URL`` points at.
Django >= 5 requires POST for logout, which the base template's form uses.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html", redirect_authenticated_user=False
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("settings/", views.settings, name="settings"),
]
