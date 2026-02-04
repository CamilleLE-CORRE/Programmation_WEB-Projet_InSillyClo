"""
Models for publication requests.
- Status: Pending, Approved, Rejected
- requested_by: User who made the request
- target: including (target_content_type, target_object_id) 
    - target_content_type: correspondence table or plasmid collection
    - target_object_id: id for target object
- cheffe_reviewed_by, cheffe_review_comment, cheffe_reviewed_at
- admin_reviewed_by, admin_review_comment, admin_reviewed_at
- created_at
"""

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError


class Publication(models.Model):
    class Status(models.TextChoices):
        PENDING_CHEFFE = 'PENDING_CHEFFE', 'Pending (Cheffe)'
        REJECTED_BY_CHEFFE = 'REJECTED_BY_CHEFFE', 'Rejected by cheffe'
        PENDING_ADMIN = 'PENDING_ADMIN', 'Pending (Admin)'
        REJECTED_BY_ADMIN = 'REJECTED_BY_ADMIN', 'Rejected by admin'
        APPROVED = 'APPROVED', 'Approved'

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
        #default=Status.PENDING_CHEFFE,
        db_index=True,
    )

    # Cheffe review firstly
    cheffe_reviewed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cheffe_reviewed_publications'
        )
    cheffe_review_comment = models.TextField(blank=True)
    cheffe_reviewed_at = models.DateTimeField(null=True, blank=True)
    # Then admin review
    admin_reviewed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='admin_reviewed_publications'
    )
    admin_review_comment = models.TextField(blank=True)
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

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
                condition=Q(
                    status__in=[
                        "PENDING_CHEFFE",
                        "PENDING_ADMIN",
                    ]
                ),
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
        if self.status == self.Status.REJECTED_BY_CHEFFE and not self.cheffe_review_comment:
            raise ValidationError("A comment is required when the cheffe rejects a request.")

        if self.status == self.Status.REJECTED_BY_ADMIN and not self.admin_review_comment:
            raise ValidationError("A comment is required when the admin rejects a request.")

