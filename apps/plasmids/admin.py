from django.contrib import admin
from .models import Plasmid, PlasmidCollection


@admin.register(PlasmidCollection)
class PlasmidCollectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_public")
    search_fields = ("name",)


@admin.register(Plasmid)
class PlasmidAdmin(admin.ModelAdmin):
    list_display = ("identifier", "name", "type", "length", "collection", "is_public")
    list_filter = ("collection", "is_public", "type")
    search_fields = ("identifier", "name")
    list_editable = ("collection",)  
