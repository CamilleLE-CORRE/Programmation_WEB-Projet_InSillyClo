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
from django.contrib
