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
-owner (Foreign Key to User)
-created_at (DateTime)
"""

from django.db import models
from apps.accounts.models import User
from apps.campaigns.models import CampaignTemplate


class Campaign(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=200)  # Name of the campaign
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,  # If the user is deleted, delete their campaigns as well
        related_name='campaigns'
    )  # Foreign key to User model
    template = models.ForeignKey(
        'campaigns.CampaignTemplate',
        on_delete=models.CASCADE,  # If the template is deleted, delete associated campaigns as well
        related_name='campaigns'
    )  # Foreign key to CampaignTemplate model
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the campaign was created

    produced_plasmids = models.ManyToManyField(
        'plasmids.Plasmid',
        related_name='campaigns',
        blank=True
    )  # Many-to-many relationship with Plasmid model

    parameters = models.JSONField(default=dict, blank=True)
    results_data = models.JSONField(default=dict, blank=True)

    collections_used = models.ManyToManyField(
        'plasmids.PlasmidCollection',
        blank=True,
        related_name='campaigns'
    )

    output_files = models.JSONField(default=dict, blank=True)


    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        #indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Campaign"  # Singular name
        verbose_name_plural = "Campaigns"  # Plural name

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.email})"
    

class CampaignResult(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    campaign = models.ForeignKey(
        'Campaign', 
        on_delete=models.CASCADE,  # If the campaign is deleted, delete associated results as well
        related_name='results'
    )  # Foreign key to Campaign model
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,  # If the user is deleted, delete their campaign results as well
        related_name='campaign_results'
    )  # Foreign key to User model
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the result was created

    class Meta:
        ordering = ('id', 'created_at')  # Default ordering by id and created_at
        #indexes = (('id',), ('created_at',))  # Indexes for id and created_at fields
        verbose_name = "Campaign Result"  # Singular name
        verbose_name_plural = "Campaign Results"  # Plural name

    def __str__(self):
        return f"Result of {self.campaign.name} (Owner: {self.owner.email})"