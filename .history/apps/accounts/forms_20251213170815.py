"""
Docstring for apps.accounts.forms.
Define forms for user account management, including registration, login, and profile update forms:
- email (Primary Key)
-firstname
-lastname
-passeword
-date of birth
-role (administratrice, user, cheffe,guest)
...
"""
from django import forms
from .models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model() # Get the custom user model

class CustomUserCreationForm(UserCreationForm):
    """
    Signup form for creating a new user account.(email, firstname, lastname, password, date of birth, role)
    """

    class Meta:
        model = User
        fields = ('email', 'firstname', 'lastname', 'date_of_birth', 'role')

        def clean_email(self):
            email = self