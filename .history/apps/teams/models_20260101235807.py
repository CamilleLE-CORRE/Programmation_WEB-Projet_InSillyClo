"""
Models for the Teams app.
Define database models for teams:
-id (Primary Key)
-name
-owner (Foreign Key to User)

!!! setting.py中缺少信息
"""

from django.db import models

class Team(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=100)  # Team name field
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE, # If the user is deleted, delete their teams as well
        related_name='teams'
    )  # Foreign key to User model

    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        #indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Team"  # Singular name
        verbose_name_plural = "Teams"  # Plural name

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.email})"

