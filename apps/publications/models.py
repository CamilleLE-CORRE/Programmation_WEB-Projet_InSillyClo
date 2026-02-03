from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.conf import settings



class Publication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    requested_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='requested_publications'
    )

    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey('target_content_type', 'target_object_id')

    status = models.CharField(
    max_length=32,
    choices=Status.choices,
    default=Status.PENDING,
    )


    team = models.ForeignKey("accounts.Team", null=True, blank=True, on_delete=models.SET_NULL)
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
        ordering = ('-created_at',)
        verbose_name = "Publication request"
        verbose_name_plural = "Publication requests"

        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['target_content_type', 'target_object_id']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['target_content_type', 'target_object_id'],
                condition=Q(status="PENDING"),
                name='unique_pending_publication_request',
            )
        ]

    def __str__(self):
        return f"Publication {self.id} requested by {self.requested_by.email}"

    def approve(self, reviewer):
        self.status = self.Status.APPROVED
        self.decided_by = reviewer
        self.rejection_reason = ''
        self.decided_at = timezone.now()
        self.full_clean()
        self.save()


    def reject(self, reviewer, comment):
        self.status = self.Status.REJECTED
        self.decided_by = reviewer
        self.rejection_reason = comment or ''
        self.decided_at = timezone.now()
        self.full_clean()
        self.save()


    def clean(self):
        # Only allow 2 targets: PlasmidCollection and Correspondence
        allowed = {
            ('plasmids', 'plasmidcollection'),
            ('correspondences', 'correspondence'),
        }

        app_label = self.target_content_type.app_label
        model_name = self.target_content_type.model

        if (app_label, model_name) not in allowed:
            raise ValidationError(f"Invalid target type: {app_label}.{model_name}")

        # If rejected, require a comment
        if self.status == self.Status.REJECTED and not self.rejection_reason:
            raise ValidationError(
                "A comment is required when rejecting a publication request."
            )
