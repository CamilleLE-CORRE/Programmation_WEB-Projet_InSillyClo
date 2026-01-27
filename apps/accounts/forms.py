from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group 

User = get_user_model()


class SignUpForm(UserCreationForm):

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",          
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "date_of_birth", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # enlever guest du choix
        if "role" in self.fields:
            self.fields["role"].choices = [
                ("user", "User"),
                ("administratrice", "Administratrice"),
            ]

    def save(self, commit=True):
        user = super().save(commit=False)

        # FIX: username unique requis -> le remplir
        if hasattr(user, "username") and not user.username:
            user.username = user.email

        if user.role == "administratrice":
            user.is_staff = True

        if commit:
            user.save()
            if user.role == "administratrice":
                group, _ = Group.objects.get_or_create(name="Administratrices")
                user.groups.add(group)

        return user




class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "date_of_birth")
        widgets = { ... }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True





