"""
Models for the Plasmids app.
Define database models for plasmids:
-id (Primary Key)
-identifier: ex. PYK23
-name: ex. Venus
-type: ex. 1a, 2b...
-sequence: DNA sequence
-is_public: boolean
"""

from django.db import models
from apps.accounts.models import User
from apps.teams.models import Team


class Plasmid(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    identifier = models.CharField(max_length=100, unique=True)  # Unique identifier for the plasmid
    name = models.CharField(max_length=200)  # Name of the plasmid
    type = models.CharField(max_length=50)  # Type of the plasmid
    sequence = models.TextField()  # DNA sequence of the plasmid
    is_public = models.BooleanField(default=False)  # Public visibility flag

    class Meta:
        ordering = ('id', 'identifier')  # Default ordering by id and identifier
        indexes = (('id',), ('identifier',))  # Indexes for id and identifier fields
        verbose_name = "Plasmid"  # Singular name
        verbose_name_plural = "Plasmids"  # Plural name

    def __str__(self):
        return f"{self.identifier} - {self.name}"