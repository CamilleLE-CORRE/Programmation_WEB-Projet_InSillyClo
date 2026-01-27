from django.urls import path

from .views import (
    TeamAddMemberView,
    TeamCreateView,
    TeamDetailView,
    TeamListView,
    TeamRemoveMemberView,
    TeamTransferOwnerView, 
)

app_name = "teams"

urlpatterns = [
    path("", TeamListView.as_view(), name="teams"),
    path("create/", TeamCreateView.as_view(), name="create_team"),
    path("<int:pk>/", TeamDetailView.as_view(), name="team_detail"),

    # actions (POST)
    path("<int:pk>/add-member/", TeamAddMemberView.as_view(), name="add_member"),
    path("<int:pk>/remove-member/", TeamRemoveMemberView.as_view(), name="remove_member"),

    # option : transfert de propriété
    path("<int:pk>/transfer-owner/", TeamTransferOwnerView.as_view(), name="transfer_owner"),
]
