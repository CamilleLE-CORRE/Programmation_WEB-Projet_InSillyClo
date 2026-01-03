<<<<<<< HEAD
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
from apps.teams.models import Team


class User(AbstractUser):
    ROLE_CHOICES = [
        ("administratrice","Administratrice"),
        ("cheffe","Cheffe"),
        ("user","User"),
        ("guest","Guest"),
    ]

    id = models.AutoField(primary_key=True)  # Primary key field

    email = models.EmailField(unique=True)  # Email field must be unique
    
    date_of_birth =  models.DateField(
        null=True, 
        blank=True
    )  # Date of birth field
    
    role = models.CharField(
        max_length=20, 
        verbose_name="Role",
        choices=ROLE_CHOICES, 
        default="guest"
    )

    USERNAME_FIELD = 'email'  # Use email as the username field
    REQUIRED_FIELDS = ['username']  # Username is still required

    class Meta:
        ordering = ('id','email')  # Default ordering by id and email
        #indexes = (('id',),('email',))  # Indexes for id and email fields
        verbose_name = "User"  # Singular name
        verbose_name_plural = "Users"  # Plural name

    teams = models.ManyToManyField(
        Team,
        related_name='members',
        blank=True
    )  # Many-to-many relationship with Team model

    # One user can create multiple simulations(campaign) 
    # campaign = models.ManyToManyField(......)

    # One user can possede nultiple plasmide collections
    # plasmide_collections = models.ManyToManyField(......)

    #One user can create multiple Campaign templates
    # campaign_templates = models.ManyToManyField(......)

    # One user can possede multiple campaign results
    # campaign_results = models.ManyToManyField(......)

    # One user can possede multiple correspondence table
    # correspondence_tables = models.ManyToManyField(......)

    def __str__(self):
        return f"{self.email} ({self.role})"
    

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


