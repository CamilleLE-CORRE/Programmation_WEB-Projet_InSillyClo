from django.conf import settings
from django.db import models


class Team(models.Model):

    name = models.CharField(max_length=255, db_index=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_teams",
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="teams",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """
        Après sauvegarde, on force l'owner à être membre.
        (On le fait après super().save() pour avoir un pk.)
        """
        creating = self.pk is None
        super().save(*args, **kwargs)

        # Garantit que l'owner est membre (idempotent)
        if self.owner_id:
            self.members.add(self.owner)
