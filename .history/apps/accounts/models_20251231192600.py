"""
Accounts app models.
Define database models for user accounts, including user profiles and account settings:
-id (Primary Key)
- email (Unique)
-firstname
-lastname
-passeword
-date of birth
-role (administratrice, user, cheffe,guest)
...
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager   # Django自带的包，继承它可以更方便创建用户

# Create my user:""""
"""class User(AbstractUser):
    username = None  # We don't use username field
    email = models.EmailField(primary_key=True, unique=True)
    firstname = models.CharField(max_length=30)
    lastname = models.CharField(max_length=30)
    date_of_birth = models.DateField( null=True, # 允许为空
        blank=True,   #允许为空
        verbose_name="Date of birth")
    
    ROLE_CHOICES = [
        ('administratrice', 'Administratrice'),
        ('user', 'User'),
        ('cheffe', 'Cheffe'),
        ('guest', 'Guest'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstname', 'lastname','role']

    def __str__(self):
        return self.email
"""