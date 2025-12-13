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
    role = forms.ChoiceField(choi)   

    class Meta:
        model = User
        fields = ('email', 'firstname', 'lastname', 'date_of_birth', 'role')

        def clean_email(self):
            email = self.cleaned_data.get('email').strip().lower() # Normalize email
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("Email is already in use.")
            return email
        
        def save(self, commit=True):
            user = super().save(commit=False) # Call the parent save method
            user.email = self.cleaned_data['email'].strip().lower() # Normalize email
            user.firstname = self.cleaned_data.get('firstname').strip()
            user.lastname = self.cleaned_data.get('lastname').strip()
            user.date_of_birth = self.cleaned_data.get('date_of_birth')
            user.role = self.cleaned_data.get('role')

            if commit:
                user.save() # Save the user to the database 
            return user
    


class CustomAuthenticationForm(AuthenticationForm):
    """
    Login form for authenticating existing users.(email, password)
    """
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={"autofocus": True}))

   