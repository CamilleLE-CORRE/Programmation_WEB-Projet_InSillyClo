"""
Models for the publications app:
- requested_by: user (FK to User model)
- target_type (collection / correspondence)
- target_id
- reviewed_by: user (FK to User model)
- reviewed_comment: text
"""

from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

import apps


class Publication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    requested_by = models.ForeignKey(
        'apps.accounts.models.User', 
        on_delete=models.CASCADE,
        related_name='requested_publications'
    )  # Foreign key to User model for requester
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )  # Content type for generic relation
    target_object_id = models.PositiveIntegerField()  # ID for generic relation
    target = GenericForeignKey('target_content_type', 'target_object_id')  # Generic foreign

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        'apps.accounts.models.User', 
        on_delete=models.SET_NULL,
        related_name='reviewed_publications',
        null=True,
        blank=True
    )  # Foreign key to User model for reviewer
    reviewed_comment = models.TextField(blank=True)  # Reviewer's comment
    created_at = models.DateTimeField(default=timezone.now)  # Timestamp of creation
    reviewed_at = models.DateTimeField(null=True, blank=True)  # Timestamp of review

    class Meta:
        ordering = ('- created_at',)  # Default ordering by id
        verbose_name = "Publication request"  # Singular name
        verbose_name_plural = "Publications requests"  # Plural name
        indeexes = {
            models.Index(fields=['status']),
            models.Index(fields=['target_content_type', 'target_object_id']),
            constraints=[
                # Prevent multiple pending requests for the same target
                feilds=['target_content_type', 'target_object_id', 'status'],
                name='unique_pending_publication_request',
                condition=models.Q(status=Status.PENDING)
            ]
        }

    def __str__(self):
        return f"Publication {self.id} requested by {self.requested_by.email}"

    def approuve(self, reviwer):
        self.status = self.Status.APPROVED
        self.reviewed_by = reviwer
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, reviwer, comment=''):
        self.status = self.Status.REJECTED
        self.reviewed_by = reviwer
        self.reviewed_comment = comment
        self.reviewed_at = timezone.now()
        self.save()

    def clean(self):
        """
        Only allowed 2 targets: collection and correspondence
        """

        models = self.target_content_type.model_class()
        allowed = {
            "correspondences":{"apps.correspondences.models.Correspondence"},
            "plasmidcollections":{"apps.plasmids.models.PlasmidCollection"}
        }
        app_label = self.target_content_type.app_label
        model_name = self.target_content_type.model

        if app_label not in allowed or model_name not in allowed[app_label]:
            raise ValidationError(f"Invalid target type: {app_label}.{model_name}")
        
        # If rejected, require a comment
        if self.status == self.Status.REJECTED and not self.reviewed_comment:
            raise ValidationError("A comment is required when rejecting a publication request.")