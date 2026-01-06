"""
Models for the Correspondences app.
Define database models for correspondences here:
-id (Primary Key)   
-name
-owner (Foreign Key to User)
-is_public: boolean

Define database models for correspondencesEntry here:
-correspondence(Foreign Key to Correspondence)
-identifier: string, plasmid id
-desplay_name : string, name shown to user
-entry_type
"""

from django.db import models

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
    
class CorrespondenceEntry(models.Model):
    """
    One roe in a correspondence
    identifier <-> desplay_name + type
    """
    correspondence = models.ForeignKey(
        Correspondence, 
        on_delete=models.CASCADE,  # If the correspondence is deleted, delete its entries as well
        related_name='entries'
    )  # Foreign key to Correspondence model

    identifier = models.CharField(max_length=100)  # Plasmid ID
    display_name = models.CharField(max_length=200)  # Name shown to user
    entry_type = models.CharField(max_length=100)  # Type of the entry

    class Meta:
        ordering = ('correspondence_id','identifier')  # Default ordering by id
        constraints = [
            models.UniqueConstraint(
                fields=['correspondence', 'identifier'],
                name='unique_correspondence_identifier'
                )
        ] # Unique constraint to ensure identifier uniqueness within a correspondence
        verbose_name = "Correspondence Entry"  # Singular name
        verbose_name_plural = "Correspondence Entries"  # Plural name

    def __str__(self):
        t = f"[{self.entry_type}] " if self.entry_type else ""
        return f"{t}{self.identifier} <-> (ID: {self.display_name})"