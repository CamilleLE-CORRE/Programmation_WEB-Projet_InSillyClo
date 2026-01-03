from django.urls import path
from .views import TeamsListView, TeamCreateView

app_name = "teams"

urlpatterns = [
    path("", TeamsListView.as_view(), name="teams"),
    path("create/", TeamCreateView.as_view(), name="create"),
]
