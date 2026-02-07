"""
Create and upload correspondence forms
"""
from django import forms
from .models import Correspondence

class CorrespondenceCreateForm(forms.ModelForm):
    class Meta:
        model = Correspondence
        fields = ['name','team']  # Fields to be included in the form
        exclude = ["is_public"]


class CorrespondenceUploadForm(forms.Form):
    file = forms.FileField(help_text="Upload a correspondence file (2 or 3 columns).")
    replace_existing = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Replace all existing entries in this correspondence.",
    ) # Checkbox to indicate if existing entries should be replaced