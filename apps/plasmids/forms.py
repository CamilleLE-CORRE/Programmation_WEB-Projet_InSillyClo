# forms.py
from django import forms

from apps.plasmids.models import Plasmid
from apps.teams.models import Team
from .models import PlasmidCollection

PLASMID_TYPE_CHOICES = [
    ('conl', 'ConL'),
    ('promoter', 'Promoter'),
    ('gene', 'Gene'),
    ('terminator', 'Terminator'),
    ('conr', 'ConR'),
    ('backbone', 'Backbone')
]

# PLASMID_TYPE_CHOICES = [
#     ('conl', 'ConL - Type 1')
#     ('promoter', 'Promoter - Type 2, 2a, 2b'),
#     ('gene', 'Gene - Type 3, 3a, 2b'),
#     ('terminator', 'Terminator - Type 4, 4a, 4b'),
#     ('conr', 'ConR - Type 5'),
#     ('backbone', 'Backbone - Type 6, 7, 8')
# ]

RESTRICTION_SITE_CHOICES = [
    ('BsaI', 'BsaI'),
    ('NotI', 'NotI'),
    ('EcoRI', 'EcoRI'),
    # à compléter avec les ER d'intérêt
]

# PRESENCE_CHOICES = [
#     ('yes', 'Yes'),
#     ('no', 'No'),
#     ('indifferent', 'Indifférent'),
# ]

class PlasmidSearchForm(forms.Form):

    sequence_pattern = forms.CharField(
        label="Nucleotide sequence motif (min. 3 residues)",
        required=False,
        min_length=3,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: ATG',
            'class': 'form-input',
        })
    )

    name = forms.CharField(
        label="Name or Sub-chain",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: pYTK081',
            'class': 'form-input',
        })
    )

    # MAINTENANT GERES DANS LE HTML POUR TABLEAU INTERACTIF
    # Types
    # for t in PLASMID_TYPE_CHOICES:
    #     locals()[f"type_{t[0]}"] = forms.ChoiceField(
    #         label=f"{t[1]}",
    #         choices=PRESENCE_CHOICES,
    #         required=False,
    #         widget=forms.Select(attrs={'class': 'form-select'})
    #     )

    # ER Sites
    # for s in RESTRICTION_SITE_CHOICES:
    #     locals()[f"site_{s[0]}"] = forms.ChoiceField(
    #         label=f"{s[1]}",
    #         choices=PRESENCE_CHOICES,
    #         required=False,
    #         widget=forms.Select(attrs={'class': 'form-select'})
    #     )

# ==============================================
# Form to add plasmids to a collection
class AddPlasmidsToCollectionForm(forms.Form):
    plasmids = forms.ModelMultipleChoiceField(
        queryset=Plasmid.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select plasmids to add"
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", Plasmid.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["plasmids"].queryset = queryset


class ImportPlasmidsForm(forms.Form):
    file = forms.FileField(
        help_text="Upload a .gb/.gbk file or a .zip containing multiple .gb/.gbk files."
    )

    target_collection = forms.ModelChoiceField(
        queryset=PlasmidCollection.objects.none(),
        required=False,
        help_text="Choose an existing collection (optional)."
    )

    new_collection_name = forms.CharField(
        max_length=255,
        required=False,
        help_text="Or create a new collection with this name (optional)."
    )

    team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        required=False,
        help_text="Choose a team (required if creating a new collection)."
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit collections to those owned by the user
        if user is not None:
            self.fields["target_collection"].queryset = PlasmidCollection.objects.filter(owner=user)
            self.fields["team"].queryset = Team.objects.filter(members=user)

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get("target_collection")
        new_name = (cleaned.get("new_collection_name") or "").strip()
        team = cleaned.get("team")

        if target and new_name:
            raise forms.ValidationError("Please choose only one way: either select an existing collection or provide a new collection name.")
        if new_name and not team:
            raise forms.ValidationError("Please select a team when creating a new collection.")
        return cleaned

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = (f.name or "").lower()

        if not (name.endswith(".gb") or name.endswith(".gbk") or name.endswith(".zip")):
            raise forms.ValidationError("Only .gb/.gbk or .zip files are allowed.")

        return f