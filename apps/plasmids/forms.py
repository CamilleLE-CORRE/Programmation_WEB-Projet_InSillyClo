from django import forms

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
            "placeholder": "Ex: pYTK081",
            "class": "form-input",
        })
    )