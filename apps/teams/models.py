from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_teams"
    )

    members = models.ManyToManyField(
        User,
        related_name="member_teams",
        blank=True
    )   


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self):
        return self.name
