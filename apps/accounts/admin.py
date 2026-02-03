from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.db.models import Count


User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_superuser", "is_active")
    search_fields = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_superuser", "is_active"),
        }),
    )

    # On enlève username des configs héritées
    fieldsets = tuple(fs for fs in fieldsets)

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
