from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError


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
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='reviewed_publications',
        null=True,
        blank=True
    )
    reviewed_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)

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
        self.reviewed_by = reviewer
        self.reviewed_comment = ''
        self.reviewed_at = timezone.now()
        self.full_clean()
        self.save()

    def reject(self, reviewer, comment):
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_comment = comment or ''
        self.reviewed_at = timezone.now()
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
        if self.status == self.Status.REJECTED and not self.reviewed_comment:
            raise ValidationError("A comment is required when rejecting a publication request.")
