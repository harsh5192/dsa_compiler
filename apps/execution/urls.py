from django.urls import path

from . import views

app_name = "execution"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("run/", views.run, name="run"),
    path("submit/", views.submit, name="submit"),
    path("save/", views.save_code, name="save-code"),
    path("starter/<slug:slug>/", views.starter, name="starter"),
]
