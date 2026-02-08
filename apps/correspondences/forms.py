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
                self.fields["team"].required = False
                self.fields["team"].help_text = (
                    "Optional. Select a team to share this correspondence table with its members. Leave it empty to keep it personal."

                )
            else:
                self.fields["team"].queryset = Team.objects.none()


class CorrespondenceUploadForm(forms.Form):
    file = forms.FileField(
        label="File",
        help_text="CSV / TSV / TXT / XLSX file with 2 or 3 columns.",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    replace_existing = forms.BooleanField(
        required=False,
        initial=True,
        label="Replace all existing entries in this correspondence.",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
)
