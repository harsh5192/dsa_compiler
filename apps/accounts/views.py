"""Local username/password accounts.

The platform is a single-user (or few-user) offline install, so authentication is
Django's stock local auth: no external identity provider, no network calls.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.problems.models import UserPreference

EDITOR_THEMES = ("vs-dark", "vs", "hc-black", "hc-light")


class RegisterForm(UserCreationForm):
    """Username + password + confirm, with an optional display name."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autofocus"] = True
        self.fields["username"].help_text = "Letters, digits and @/./+/-/_ only."


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserPreference.for_user(user)
        login(request, user)
        messages.success(request, f"Welcome, {user.username}. Happy solving.")
        return redirect("dashboard:index")
    return render(request, "accounts/register.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def settings(request):
    """Theme, default language and editor preferences."""
    from apps.execution.models import Language

    preference = UserPreference.for_user(request.user)
    languages = Language.objects.enabled()

    def _int(name, default, low, high):
        try:
            return max(low, min(high, int(request.POST.get(name, default))))
        except (TypeError, ValueError):
            return getattr(preference, name, default)

    def _float(name, default, low, high):
        try:
            return max(low, min(high, float(request.POST.get(name, default))))
        except (TypeError, ValueError):
            return getattr(preference, name, default)

    if request.method == "POST":
        theme = request.POST.get("theme", preference.theme)
        if theme in dict(UserPreference.THEME_CHOICES):
            preference.theme = theme

        editor = request.POST.get("editor", preference.editor)
        if editor in ("monaco", "plain"):
            preference.editor = editor

        editor_theme = request.POST.get("editor_theme", preference.editor_theme)
        if editor_theme in EDITOR_THEMES:
            preference.editor_theme = editor_theme

        preference.editor_font_size = _int("editor_font_size", preference.editor_font_size, 10, 28)
        preference.autosave_delay_ms = _int("autosave_delay_ms", preference.autosave_delay_ms, 300, 10_000)
        preference.execution_timeout = _float("execution_timeout", preference.execution_timeout, 0.5, 60.0)

        preference.autosave = request.POST.get("autosave") == "on"
        preference.show_editor_intro = request.POST.get("show_editor_intro") == "on"
        preference.keyboard_shortcuts = request.POST.get("keyboard_shortcuts") == "on"

        # ``default_language`` is a foreign key: resolve the submitted slug to a
        # row instead of assigning the raw string, which Django would reject.
        slug = (request.POST.get("default_language") or "").strip()
        preference.default_language = next((l for l in languages if l.slug == slug), None)

        preference.save()
        messages.success(request, "Preferences saved.")
        return redirect("accounts:settings")

    return render(
        request,
        "accounts/settings.html",
        {
            "preference": preference,
            "languages": languages,
            "editor_themes": EDITOR_THEMES,
            "theme_choices": UserPreference.THEME_CHOICES,
        },
    )
