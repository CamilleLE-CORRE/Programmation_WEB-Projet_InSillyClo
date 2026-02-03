from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import CreateView, TemplateView, DetailView, ListView, UpdateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from apps.simulations.models import Campaign
from apps.plasmids.models import PlasmidCollection
from apps.correspondences.models import Correspondence
from apps.publications.models import Publication


from .forms import (
    SignUpForm,
    EmailAuthenticationForm,
    ProfileForm,
    TeamAddMemberForm,
    TeamCreateForm,
    TeamTransferOwnerForm,
)
from .models import Team

User = get_user_model()


# =========================
# AUTH
# =========================

class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"


class EmailLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class SignUpView(CreateView):
    model = User
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")


# =========================
# PROFILE
# =========================

class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user


# =========================
# TEAMS – ADMIN
# =========================

def admin_team_list(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden("Access denied")

    teams = (
        Team.objects
        .select_related("owner")
        .prefetch_related("members")
        .order_by("-id")
    )

    return render(request, "admin_team_list.html", {"teams": teams})


def admin_team_detail(request, pk):
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden("Access denied")

    team = get_object_or_404(
        Team.objects.select_related("owner").prefetch_related("members"),
        pk=pk,
    )

    return render(
        request,
        "admin_team_detail.html",
        {
            "team": team,
            "members": team.members.all().order_by("email"),
        },
    )


# =========================
# TEAMS – MIXINS
# =========================

class TeamMemberRequiredMixin(LoginRequiredMixin):
    team = None

    def get_team(self):
        if self.team is None:
            self.team = get_object_or_404(
                Team.objects.select_related("owner"),
                pk=self.kwargs["pk"],
            )
        return self.team

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)

        team = self.get_team()
        if not team.members.filter(pk=request.user.pk).exists():
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class TeamOwnerRequiredMixin(TeamMemberRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        team = self.get_team()
        if not request.user.is_staff and team.owner_id != request.user.id:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


# =========================
# TEAMS – USER
# =========================

class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = "accounts/teams.html"  
    context_object_name = "teams"

    def get_queryset(self):
        return (
            Team.objects
            .filter(members=self.request.user)
            .select_related("owner")
            .distinct()
            .order_by("name")
        )


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamCreateForm
    template_name = "accounts/create_team.html"  

    @transaction.atomic
    def form_valid(self, form):
        team = form.save(commit=False)
        team.owner = self.request.user
        team.save()
        messages.success(self.request, "Équipe créée.")
        return redirect("accounts:team_detail", pk=team.pk)


class TeamDetailView(TeamMemberRequiredMixin, DetailView):
    model = Team
    template_name = "accounts/team_detail.html"
    context_object_name = "team"

    def get_queryset(self):
        return Team.objects.select_related("owner").prefetch_related("members")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = self.object

        ctx["is_owner"] = team.owner_id == self.request.user.id
        ctx["add_member_form"] = TeamAddMemberForm(team=team)
        ctx["transfer_owner_form"] = TeamTransferOwnerForm(team=team)
        ctx["members"] = team.members.all().order_by("email")

        # === NOUVEAU ===

        ctx["campaigns"] = Campaign.objects.filter(
            owner__in=team.members.all()
        ).select_related("template").distinct()

        ctx["collections"] = PlasmidCollection.objects.filter(
            team=team
        )

        ctx["correspondences"] = (
            Correspondence.objects
            .filter(owner__in=team.members.all())
            .select_related("owner")
            .distinct()
        )


        ctx["publication_requests"] = Publication.objects.filter(
            team=team
        ).select_related("requested_by")

        return ctx



class TeamAddMemberView(TeamOwnerRequiredMixin, View):
    def post(self, request, pk):
        team = self.get_team()
        form = TeamAddMemberForm(request.POST, team=team)

        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return redirect("accounts:team_detail", pk=pk)

        team.members.add(form.user)
        messages.success(request, "Membre ajouté.")
        return redirect("accounts:team_detail", pk=pk)


class TeamRemoveMemberView(TeamOwnerRequiredMixin, View):
    def post(self, request, pk):
        team = self.get_team()
        user_id = request.POST.get("user_id")

        if not user_id or str(team.owner_id) == str(user_id):
            messages.error(request, "Action interdite.")
            return redirect("accounts:team_detail", pk=pk)

        team.members.remove(user_id)
        messages.success(request, "Membre retiré.")
        return redirect("accounts:team_detail", pk=pk)


class TeamTransferOwnerView(TeamOwnerRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        team = self.get_team()
        form = TeamTransferOwnerForm(request.POST, team=team)

        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return redirect("accounts:team_detail", pk=pk)

        new_owner = form.cleaned_data["new_owner"]
        team.members.add(new_owner)
        team.owner = new_owner
        team.save()

        messages.success(request, "Propriété transférée.")
        return redirect("accounts:team_detail", pk=pk)
