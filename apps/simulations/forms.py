from django import forms

class SimulationForm(forms.Form):
    """Form for simulation validation"""
    
    template_file = forms.FileField(
        label="Campaign Template",
        help_text="XLSX or CSV file",
        required=True
    )
    
    sequences_archive = forms.FileField(
        label="Plasmid Sequences",
        help_text="ZIP archive with GenBank files",
        required=False
    )
    
    correspondence_file = forms.FileField(
        label="Correspondence Table",
        help_text="CSV file mapping IDs to names",
        required=False
    )
    
    pcr_primers = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="One primer per line"
    )
    
    digestion_enzymes = forms.CharField(
        required=False,
        help_text="Comma-separated enzyme names"
    )
    
    default_concentration = forms.FloatField(
        required=False,
        min_value=0,
        initial=100
    )
    
    def clean_template_file(self):
        file = self.cleaned_data['template_file']
        ext = file.name.split('.')[-1].lower()
        if ext not in ['xlsx', 'csv']:
            raise forms.ValidationError("Only XLSX and CSV files are allowed for templates.")
        return file
    
    def clean_sequences_archive(self):
        file = self.cleaned_data.get('sequences_archive')
        if file:
            if not file.name.endswith('.zip'):
                raise forms.ValidationError("Sequences must be in a ZIP archive.")
        return file