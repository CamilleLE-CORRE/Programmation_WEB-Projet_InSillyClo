from django import forms
from .models import CampaignTemplate


class CampaignTemplateForm(forms.ModelForm):
    template_type = forms.ChoiceField(
        choices=CampaignTemplate.TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'template-type'}),
        required=True,
        label='Template Type',
    )

    DOWNLOAD_CHOICES = [
        ('xlsx', 'Excel (.xlsx)')
    ]

    download_format = forms.ChoiceField(
        choices=DOWNLOAD_CHOICES,
        widget=forms.HiddenInput,
        initial='xlsx',
        required=False,
        label='Download format',
    )

    class Meta:
        model = CampaignTemplate
        fields = ['name', 'template_type', 'restriction_enzyme', 'separator']
        widgets = {
            'separator': forms.TextInput(attrs={'value': '.', 'maxlength': 2, 'placeholder': 'Ex : "-"'}),
            'restriction_enzyme': forms.TextInput(attrs={'placeholder': 'Ex : BsaI, BsmBI'}),
            'name': forms.TextInput(attrs={'placeholder': 'Ex : my_assembly'}),
        }
        labels = {
            'name': 'Template Name',
            'template_type': 'Template Type',
            'restriction_enzyme': 'Restriction Enzyme',
            'separator': 'Separator',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = kwargs.get('data')
        template_type = None
        if data:
            template_type = data.get('template_type')
        else:
            template_type = self.initial.get('template_type') or (getattr(self.instance, 'template_type', None) if getattr(self, 'instance', None) else None)

        self.fields['separator'].required = True

    def clean_template_type(self):
        t = self.cleaned_data.get('template_type')
        valid_keys = [k for k, _ in CampaignTemplate.TYPE_CHOICES]
        if not t or t not in valid_keys:
            raise forms.ValidationError('Please choose a valid template type.')
        return t

    def clean(self):
        cleaned = super().clean()
        sep = cleaned.get('separator')
        if not sep:
            self.add_error('separator', 'Separator is required.')
        return cleaned

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            qs = CampaignTemplate.objects.filter(name__iexact=name)
            if getattr(self.instance, 'pk', None):
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A template with this name already exists.')
        return name