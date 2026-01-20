from django import forms
from django.contrib.auth import get_user_model

from .models import Team

User = get_user_model()


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name"]


class TeamAddMemberForm(forms.Form):
    """
    Ajout d'un membre par email.
    Valide si email existant et si utilisateur pas déjà membre de l'équipe.
    """
    email = forms.EmailField()

    def __init__(self, *args, team: Team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self._user = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Aucun utilisateur avec cet email.")

        # déjà membre ?
        if self.team.members.filter(pk=user.pk).exists():
            raise forms.ValidationError("Cet utilisateur est déjà membre de l’équipe.")

        self._user = user
        return email

    @property
    def user(self):
        return self._user


class TeamTransferOwnerForm(forms.Form):
    """
    Transfert de propriété vers un membre existant.
    """
    new_owner = forms.ModelChoiceField(queryset=User.objects.none())

    def __init__(self, *args, team: Team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.fields["new_owner"].queryset = (
            team.members.exclude(pk=team.owner_id).order_by("email")
        )

    def clean_new_owner(self):
        user = self.cleaned_data["new_owner"]

        # doit être membre
        if not self.team.members.filter(pk=user.pk).exists():
            raise forms.ValidationError("Le nouvel owner doit être membre de l’équipe.")

        # ne doit pas être l'owner actuel
        if user.pk == self.team.owner_id:
            raise forms.ValidationError("Cet utilisateur est déjà propriétaire de l’équipe.")

        return user
