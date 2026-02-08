
from django.contrib import admin
from .models import CampaignTemplate

@admin.register(CampaignTemplate)
class CampaignTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_public", "template_type", "updated_at")
    list_editable = ("is_public",)
    list_filter = ("is_public", "template_type")
    search_fields = ("name", "owner__email")
