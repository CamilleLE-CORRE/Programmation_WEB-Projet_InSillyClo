from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

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

        # rôle administratrice -> staff
        if user.role == "administratrice":
            user.is_staff = True
            # user.is_superuser = True

        if commit:
            user.save()
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

