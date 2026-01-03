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
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager   # Django自带的包，继承它可以更方便创建用户



