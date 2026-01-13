from django.contrib import admin
from django.db.models import Count

from .models import Team, TeamMembership

# permet d'afficher les membres d'une équipe dans l'admin de l'équipe
class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    autocomplete_fields = ("user",)
    fields = ("user", "role", "created_at")
    readonly_fields = ("created_at",)

# admin pour le modèle Team : affiche le nom, le propriétaire, la date de création et 
# le nombre de membres
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "members_count")
    search_fields = ("name", "owner__email")
    list_select_related = ("owner",)
    inlines = [TeamMembershipInline]
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_members_count=Count("memberships", distinct=True))

    @admin.display(description="Members")
    def members_count(self, obj):
        return getattr(obj, "_members_count", 0)

# admin pour le modèle TeamMembership : affiche l'équipe, l'utilisateur, le rôle et 
# la date de création
@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "created_at")
    search_fields = ("team__name", "user__email")
    list_select_related = ("team", "user")
    list_filter = ("role",)
    ordering = ("-created_at",)
