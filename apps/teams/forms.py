from django import forms
from .models import Team

class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name"]

class TeamAddMemberForm(forms.Form):
    email = forms.EmailField(label="User email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No user with this email.")
        return email