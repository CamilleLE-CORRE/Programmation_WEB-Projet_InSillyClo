from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import CreateView, ListView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Team
from .forms import TeamCreateForm, TeamAddMemberForm


# Vérifie si l’utilisateur est authentifié et propriétaire de l’équipe.
def is_owner(user, team: Team) -> bool:
    return user.is_authenticated and team.owner_id == user.id


# Liste des équipes dont l’utilisateur connecté est membre.
class TeamsListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = "teams/teams.html"
    context_object_name = "teams"

    def get_queryset(self):
        return Team.objects.filter(members=self.request.user)


# Création d’une équipe.
# Définit l’utilisateur comme owner.
# Ajoute automatiquement l’owner aux membres.
class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamCreateForm
    template_name = "teams/create_team.html"
    success_url = reverse_lazy("teams:teams")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)   # self.object est créé ici
        self.object.members.add(self.request.user)
        return response

# Affichage d’une équipe / Contrôle d’accès par appartenance / Gestion d’une équipe / Ajout de membres
class TeamDetailView(LoginRequiredMixin, View):
    template_name = "teams/team_detail.html"
    
    # Affiche le détail d’une équipe.
    # Vérifie l’appartenance de l’utilisateur à l’équipe.
    # Fournit le formulaire d’ajout de membre.
    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not team.members.filter(pk=request.user.pk).exists():
            return HttpResponseForbidden("Not allowed.")

        add_form = TeamAddMemberForm()
        return render(request, self.template_name, {"team": team, "add_form": add_form})

    # Ajoute un membre à l’équipe.
    # Action réservée au owner.
    # Ajout par email utilisateur.
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)

        # seule la cheffe peut modifier l'équipe
        if not is_owner(request.user, team):
            return HttpResponseForbidden("Only the team owner can manage members.")

        add_form = TeamAddMemberForm(request.POST)
        if add_form.is_valid():
            email = add_form.cleaned_data["email"]
            user = User.objects.get(email=email)

            team.members.add(user)
            return redirect("teams:detail", pk=team.pk)

        return render(request, self.template_name, {"team": team, "add_form": add_form})


# Supprime un membre d’une équipe.
# Action réservée au owner.
# Empêche la suppression du owner.
class TeamRemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, pk, user_id):
        team = get_object_or_404(Team, pk=pk)

        if not is_owner(request.user, team):
            return HttpResponseForbidden("Only the team owner can manage members.")

        # empêcher d'enlever la cheffe elle-même
        if user_id == team.owner_id:
            return HttpResponseForbidden("Owner cannot be removed.")

        user = get_object_or_404(User, pk=user_id)
        team.members.remove(user)
        return redirect("teams:detail", pk=team.pk)

