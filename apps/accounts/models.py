from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _generate_unique_username(self, email: str) -> str:
        base = (email.split("@")[0] or "user").lower()
        candidate = base
        i = 1
        while self.model.objects.filter(username=candidate).exists():
            i += 1
            candidate = f"{base}{i}"
        return candidate

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        # si username pas fourni, on le génère (AbstractUser le garde UNIQUE)
        if not extra_fields.get("username"):
            extra_fields["username"] = self._generate_unique_username(email)

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


class User(AbstractUser):
    ROLE_CHOICES = [
        ("administratrice", "Administratrice"),
        ("cheffe", "Cheffe"),
        ("user", "User"),
    ]

    # on garde username car AbstractUser l'a, mais on ne s'en sert pas pour login
    email = models.EmailField(unique=True)

    date_of_birth = models.DateField(null=True, blank=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="user",
        verbose_name="Role",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # <-- important

    objects = UserManager()

    class Meta:
        ordering = ["id", "email"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.email} ({self.role})"
