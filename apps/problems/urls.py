from django.urls import path

from . import views

app_name = "problems"

urlpatterns = [
    path("", views.problem_list, name="list"),
    path("<slug:slug>/", views.problem_detail, name="detail"),
    path("<slug:slug>/sheet/<int:entry_id>/toggle/", views.toggle_sheet_problem, name="toggle-sheet"),
]
