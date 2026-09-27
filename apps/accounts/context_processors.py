"""Template context shared by every page."""

from django.conf import settings


def platform_settings(request):
    """Expose a few settings to templates without importing them in views."""
    from apps.problems.models import UserPreference

    preference = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        try:
            preference = UserPreference.for_user(user)
        except Exception:  # pragma: no cover - never block a page render
            preference = None

    return {
        "preference": preference,
        "platform_name": getattr(settings, "DSA_PLATFORM_NAME", "DSA Studio"),
        "platform_tagline": getattr(
            settings, "DSA_PLATFORM_TAGLINE", "Sheets, code and progress, offline."
        ),
        "editors": getattr(settings, "DSA_EDITORS", ["monaco", "plain"]),
        "default_editor": getattr(settings, "DSA_DEFAULT_EDITOR", "monaco"),
        "execution_backend": getattr(settings, "DSA_EXECUTION_BACKEND", "subprocess"),
        "debug": settings.DEBUG,
    }
