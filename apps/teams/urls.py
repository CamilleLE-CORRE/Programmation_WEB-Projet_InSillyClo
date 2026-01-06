from django.urls import path
from .views import TeamsListView, TeamCreateView, TeamDetailView, TeamRemoveMemberView

app_name = "teams"

urlpatterns = [
    path("", TeamsListView.as_view(), name="teams"),
    path("create/", TeamCreateView.as_view(), name="create"),
    path("<int:pk>/", TeamDetailView.as_view(), name="detail"),
    path("<int:pk>/remove/<int:user_id>/", TeamRemoveMemberView.as_view(), name="remove_member"),
]
