from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "date_of_birth", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # enlever guest du choix
        if "role" in self.fields:
            self.fields["role"].choices = [
                ("user", "User"),
                ("administratrice", "Administratrice"),
                ("cheffe", "Cheffe"),
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

