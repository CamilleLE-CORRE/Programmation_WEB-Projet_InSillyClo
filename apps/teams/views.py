from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView
from django.urls import reverse_lazy

from .models import Team
from .forms import TeamCreateForm


class TeamsListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = "teams/teams.html"
    context_object_name = "teams"

    def get_queryset(self):
        return Team.objects.filter(members=self.request.user)


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamCreateForm
    template_name = "teams/create_team.html"
    success_url = reverse_lazy("teams:teams")

    def form_valid(self, form):
        team = form.save(commit=False)
        team.owner = self.request.user
        team.save()
        team.members.add(self.request.user)  # cheffe = membre
        return super().form_valid(form)
