"""
Models for the campaigns app.
Define database models for campaigns here:
-id (Primary Key)
-name   
-owner (Foreign Key to User)
-template (Foreign Key to CampaignTemplate)
-created_at (DateTime)

Define campaign's results:
-id (Primary Key)
-campaign (Foreign Key to Campaign)



"""

from django.db import models
from apps.accounts.models import User
from apps.templates.models import CampaignTemplate


class Campaign(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=200)  # Name of the campaign
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,  # If the user is deleted, delete their campaigns as well
        related_name='campaigns'
    )  # Foreign key to User model
    template = models.ForeignKey(
        'templates.CampaignTemplate', 
        on_delete=models.CASCADE,  # If the template is deleted, delete associated campaigns as well
        related_name='campaigns'
    )  # Foreign key to CampaignTemplate model
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the campaign was created

    produced_plasmids = models.ManyToManyField(
        'plasmids.Plasmid',
        related_name='campaigns',
        blank=True
    )  # Many-to-many relationship with Plasmid model

    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Campaign"  # Singular name
        verbose_name_plural = "Campaigns"  # Plural name

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.email})"
