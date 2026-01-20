from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

class PublicationStatus(models.TextChoices):
    PENDING_TEAM_LEAD = "PENDING_TEAM_LEAD", "Pending team lead"
    PENDING_ADMIN = "PENDING_ADMIN", "Pending admin"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"

class PublicationRequest(models.Model):
    # cible (collection de plasmides OU table de correspondance)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="publication_requests"
    )
    status = models.CharField(
        max_length=32, choices=PublicationStatus.choices, default=PublicationStatus.PENDING_ADMIN
    )

    team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.SET_NULL)
    team_validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="publication_team_validations"
    )
    team_validated_at = models.DateTimeField(null=True, blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="publication_decisions"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="uniq_publication_request_per_target"
            )
        ]

    def __str__(self):
        return f"{self.target} [{self.status}]"
