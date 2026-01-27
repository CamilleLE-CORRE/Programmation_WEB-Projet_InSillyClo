from django.contrib import admin
from .models import CampaignTemplate


"""
Ce code est utilisé pour enregistrer le modèle CampaignTemplate 
dans l'interface d'administration Django.
Il permet aux administrateurs de gérer les modèles de campagne via 
l'interface d'administration.
"""

@admin.register(CampaignTemplate)
class CampaignTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "template_type", "restriction_enzyme", "separator", "is_public", "owner", "created_at")
    list_filter = ("template_type", "is_public")
    search_fields = ("name", "restriction_enzyme", "owner__email", "owner__username")
    ordering = ("-created_at",)

    # Assigne l'utilisateur actuel comme propriétaire du modèle lors de sa création
    # si aucun propriétaire n'est défini.
    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
        super().save_model(request, obj, form, change)
