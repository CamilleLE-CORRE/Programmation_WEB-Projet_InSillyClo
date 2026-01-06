from django.contrib import admin
from .models import Correspondence, CorrespondenceEntry

@admin.register(Correspondence)
class CorrespondenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'is_public')
    search_fields = ('name', 'owner__email')


@admin.register(CorrespondenceEntry)
class CorrespondenceEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'correspondence', 'identifier', 'display_name', 'entry_type')
    search_fields = ('identifier', 'display_name', 'correspondence__name')
    list_filter = ('entry_type','correspondence')
