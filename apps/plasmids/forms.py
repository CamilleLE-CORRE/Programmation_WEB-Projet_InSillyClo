from django import forms

from apps.plasmids.models import Plasmid
from apps.teams.models import Team
from .models import PlasmidCollection

class PlasmidSearchForm(forms.Form):
    """
    Formulaire de recherche principal.
    Les contraintes dynamiques sur les annotations
    (présence / absence + nom) sont gérées directement
    dans le template HTML et traitées dans la vue.
    """

    sequence_pattern = forms.CharField(
        label="Nucleotide sequence motif (min. 3 residues)",
        required=False,
        min_length=3,
        widget=forms.TextInput(attrs={
            "placeholder": "Ex: ATG",
            "class": "form-input",
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
