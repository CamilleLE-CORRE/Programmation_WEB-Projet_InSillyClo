from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

# Modèle représentant une équipe d'utilisateurs
class Team(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)  # pas unique
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_teams",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TeamMembership",
        # un utilisateur peut accéder à ses équipes via user.teams
        related_name="teams",
        blank=True,
    )
    # Date de création de l’équipe
    created_at = models.DateTimeField(auto_now_add=True)

    # équipes triées par date de création 
    class Meta:
        ordering = ("-created_at",)

    # affichage lisible de l’équipe
    def __str__(self) -> str:
        return self.name

    # Tout ce qui est fait dans la méthode save est exécuté comme une seule opération
    # Si une étape échoue, rien n’est enregistré
    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = self.pk is None
        old_owner_id = None

        if not creating:
            old_owner_id = (
                Team.objects.filter(pk=self.pk)
                .values_list("owner_id", flat=True)
                .first()
            )

        super().save(*args, **kwargs)

        # l'owner est toujours membre, avec role OWNER
        TeamMembership.objects.update_or_create(
            team=self,
            user=self.owner,
            defaults={"role": TeamMembership.Role.OWNER},
        )

        # Si changement d'owner : l'ancien owner (s'il existe) redevient MEMBER (s'il reste membre)
        if old_owner_id and old_owner_id != self.owner_id:
            TeamMembership.objects.filter(
                team=self,
                user_id=old_owner_id,
            ).exclude(user_id=self.owner_id).update(role=TeamMembership.Role.MEMBER)


# Modèle représentant l'appartenance d'un utilisateur à une équipe, avec un rôle
class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MEMBER = "MEMBER", "Member"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Unicité de l'association équipe-utilisateur (un utilisateur ne peut être membre 
        # qu'une fois d'une équipe)
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="uniq_team_user"),
        ]
        # Indexes pour optimiser les requêtes fréquentes
        indexes = [
            models.Index(fields=["team", "role"]),
            models.Index(fields=["user"]),
        ]
        # Tri par date de création 
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.team} - {self.user} ({self.role})"

    # Validation avant sauvegarde : le rôle OWNER ne peut concerner que le owner de l’équipe
    def clean(self):
        if self.role == self.Role.OWNER and self.team.owner_id != self.user_id:
            raise ValidationError("Seul le propriétaire de l’équipe peut avoir le rôle OWNER.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
