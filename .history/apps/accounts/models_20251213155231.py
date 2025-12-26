"""
Accounts app models.
Define database models for user accounts, including user profiles and account settings:
- email (Primary Key)
-firstname
-lastname
-passeword
-date of birth
-role (administratrice, user, cheffe,guest)
...
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager   # Django自带的包，继承它可以更方便创建用户

# Create my user:
class User(AbstractUser):
    email = models.EmailField(primary_key=True, unique=True)
    firstname = models.CharField(max_length=30)
    lastname = models.CharField(max_length=30)
    date_of_birth = models.DateField()
    
    ROLE_CHOICES = [
        ('administratrice', 'Administratrice'),
        ('user', 'User'),
        ('cheffe', 'Cheffe'),
        ('guest', 'Guest'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname', 'date_of_birth', 'role']

    def __str__(self):
        return self.email
