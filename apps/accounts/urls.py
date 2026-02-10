from django.urls import path
from .views import SignUpView, EmailLoginView, EmailLogoutView, ProfileView

app_name = "accounts"

from .views import (
    TeamAddMemberView,
    TeamCreateView,
    TeamDetailView,
    TeamListView,
    TeamRemoveMemberView,
    TeamTransferOwnerView,
    admin_team_list,
    AdminTeamDetailView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", EmailLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("", TeamListView.as_view(), name="teams"),
    path("create/", TeamCreateView.as_view(), name="create_team"),
    path("<int:pk>/", TeamDetailView.as_view(), name="team_detail"),

    # actions (POST)
    path("<int:pk>/add-member/", TeamAddMemberView.as_view(), name="add_member"),
    path("<int:pk>/remove-member/", TeamRemoveMemberView.as_view(), name="remove_member"),
    path("<int:pk>/transfer-owner/", TeamTransferOwnerView.as_view(), name="transfer_owner"),

    # ADMINISTRATOR VIEW
    path("admin/teams/", admin_team_list, name="admin_team_list"), 
    path("admin/teams/<int:pk>/", AdminTeamDetailView.as_view(), name="admin_team_detail"),

]


