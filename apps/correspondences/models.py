"""
Models for the Correspondences app.
Define database models for correspondences here:
-id (Primary Key)   
-name
-owner (Foreign Key to User)
-is_public: boolean
"""

from django.db import models
from apps.accounts.models import User

class Correspondence(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=200)  # Name of the correspondence
    owner = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE,  # If the user is deleted, delete their correspondences as well
        related_name='correspondences'
    )  # Foreign key to User model
    is_public = models.BooleanField(default=False)  # Public visibility flag

    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        #indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Correspondence"  # Singular name
        verbose_name_plural = "Correspondences"  # Plural name

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.email})"

