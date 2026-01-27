from django.contrib import admin
from django.db.models import Count

from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "members_count")
    search_fields = ("name", "owner__email", "members__email")
    list_select_related = ("owner",)
    ordering = ("-created_at",)
    filter_horizontal = ("members",)  # UI simple pour ManyToMany

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_members_count=Count("members", distinct=True))

    @admin.display(description="Members")
    def members_count(self, obj):
        return getattr(obj, "_members_count", 0)
