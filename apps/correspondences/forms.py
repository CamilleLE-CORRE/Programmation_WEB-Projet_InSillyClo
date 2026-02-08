"""
Create and upload correspondence forms
"""
from django import forms
from .models import Correspondence
from apps.accounts.models import Team
from django.db.models import Q

class CorrespondenceCreateForm(forms.ModelForm):
    class Meta:
        model = Correspondence
        fields = ["name", "team"]
        exclude = ["is_public"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if "team" in self.fields:
            if user and user.is_authenticated:
                # Teams où l'utilisateur est owner OU membre
                self.fields["team"].queryset = Team.objects.filter(
                    Q(owner=user) | Q(members=user)
                ).distinct()
            else:
                self.fields["team"].queryset = Team.objects.none()


class CorrespondenceUploadForm(forms.Form):
    file = forms.FileField(help_text="Upload a correspondence file (2 or 3 columns).")
    replace_existing = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Replace all existing entries in this correspondence.",
    ) # Checkbox to indicate if existing entries should be replaced