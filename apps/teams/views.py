from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms import TeamAddMemberForm, TeamCreateForm, TeamTransferOwnerForm
from .models import Team, TeamMembership

User = get_user_model()

# Accès réservé aux membres de l'équipe.
class TeamMemberRequiredMixin(LoginRequiredMixin):
    team: Team | None = None

    def get_team(self) -> Team:
        if self.team is not None:
            return self.team
        pk = self.kwargs.get("pk")
        team = get_object_or_404(Team.objects.select_related("owner"), pk=pk)
        self.team = team
        return team

    def dispatch(self, request, *args, **kwargs):
        team = self.get_team()
        is_member = TeamMembership.objects.filter(team=team, user=request.user).exists()
        if not is_member:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

# Accès réservé à l'owner de l'équipe (donc forcément membre).
class TeamOwnerRequiredMixin(TeamMemberRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        team = self.get_team()
        if team.owner_id != request.user.id:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

# Gestion des vues liées aux équipes
class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = "teams/teams.html"
    context_object_name = "teams"

    def get_queryset(self):
        return (
            Team.objects.filter(memberships__user=self.request.user)
            .select_related("owner")
            .distinct()
            .order_by("name")
        )


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamCreateForm
    template_name = "teams/create_team.html"

    @transaction.atomic
    def form_valid(self, form):
        team = form.save(commit=False)
        team.owner = self.request.user
        team.save()  # Team.save() crée/force le membership OWNER (invariant)
        messages.success(self.request, "Équipe créée.")
        return redirect("teams:team_detail", pk=team.pk)


class TeamDetailView(TeamMemberRequiredMixin, DetailView):
    model = Team
    template_name = "teams/team_detail.html"
    context_object_name = "team"

    def get_queryset(self):
        return (
            Team.objects.select_related("owner")
            .prefetch_related("members")
            .prefetch_related("memberships__user")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team: Team = self.object
        ctx["is_owner"] = (team.owner_id == self.request.user.id)
        ctx["add_member_form"] = TeamAddMemberForm(team=team)
        ctx["transfer_owner_form"] = TeamTransferOwnerForm(team=team)
        ctx["memberships"] = (
            TeamMembership.objects.filter(team=team)
            .select_related("user")
            .order_by("-role", "user__email")
        )
        return ctx

# Actions sur les équipes : ajout/retrait de membres, transfert de propriété
class TeamAddMemberView(TeamOwnerRequiredMixin, View):
    def post(self, request, pk: int):
        team = self.get_team()
        form = TeamAddMemberForm(request.POST, team=team)

        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err.as_text())
            return redirect("teams:team_detail", pk=team.pk)

        TeamMembership.objects.create(team=team, user=form.user, role=TeamMembership.Role.MEMBER)
        messages.success(request, "Membre ajouté.")
        return redirect("teams:team_detail", pk=team.pk)

# Retrait d'un membre (sauf l'owner)
class TeamRemoveMemberView(TeamOwnerRequiredMixin, View):
    def post(self, request, pk: int):
        team = self.get_team()
        user_id = request.POST.get("user_id")

        if not user_id:
            messages.error(request, "Utilisateur manquant.")
            return redirect("teams:team_detail", pk=team.pk)

        # Interdire de retirer l'owner
        if str(team.owner_id) == str(user_id):
            messages.error(request, "Impossible de retirer la cheffe d’équipe.")
            return redirect("teams:team_detail", pk=team.pk)

        deleted, _ = TeamMembership.objects.filter(team=team, user_id=user_id).delete()
        if deleted:
            messages.success(request, "Membre retiré.")
        else:
            messages.error(request, "Cet utilisateur n’est pas membre de l’équipe.")
        return redirect("teams:team_detail", pk=team.pk)

# Transfert de propriété de l'équipe
class TeamTransferOwnerView(TeamOwnerRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk: int):
        team = self.get_team()
        form = TeamTransferOwnerForm(request.POST, team=team)

        if not form.is_valid():
            for err in form.errors.values():
                messages.error(request, err.as_text())
            return redirect("teams:team_detail", pk=team.pk)

        new_owner = form.cleaned_data["new_owner"]
        team.owner = new_owner
        team.save()  # Team.save() force le membership OWNER sur new_owner et MEMBER sur ancien owner
        messages.success(request, "Propriété de l’équipe transférée.")
        return redirect("teams:team_detail", pk=team.pk)
