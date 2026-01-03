"""
Models for the campaigns template.
Database models for the campaigns template can be defined here:
-id (Primary Key)
-name
-owner (Foreign Key to User)
-is_public: boolean
-is_typed: boolean
"""

from django.db import models
from apps.accounts.models import User

class CampaignTemplate(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=200)  # Name of the campaign template
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,  # If the user is deleted, delete their campaign templates as well
        related_name='campaign_templates'
    )  # Foreign key to User model
    is_public = models.BooleanField(default=False)  # Public visibility flag
    is_typed = models.BooleanField(default=False)  # Typed flag

    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        #indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Campaign Template"  # Singular name
        verbose_name_plural = "Campaign Templates"  # Plural name

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.email})"
