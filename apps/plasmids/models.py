"""
Models for the Plasmids app.
Define database models for plasmids:
-id (Primary Key)
-identifier: ex. PYK23
-name: ex. Venus
-type: ex. 1a, 2b...
-sequence: DNA sequence
-is_public: boolean

Define database model for plasmidecollections:
-id (Primary Key)
-name
-owner (Foreign Key to User)
-team (Foreign Key to Team, optional)
-is_public: boolean
"""

from django.db import models
from apps.accounts.models import User
from apps.teams.models import Team


class PlasmidCollection(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    name = models.CharField(max_length=200)  # Name of the plasmid collection
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='plasmid_collections'
    )  # Foreign key to User model
    team = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE,
        related_name='plasmid_collections',
        null=True,
        blank=True
    )  # Optional foreign key to Team model
    is_public = models.BooleanField(default=False)  # Public visibility flag

    class Meta:
        ordering = ('id', 'name')  # Default ordering by id and name
        #indexes = (('id',), ('name',))  # Indexes for id and name fields
        verbose_name = "Plasmid Collection"  # Singular name
        verbose_name_plural = "Plasmid Collections"  # Plural name

    def __str__(self):
        return f"{self.name}" # (Owner: {self.owner.email})"


class Plasmid(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key field
    identifier = models.CharField(max_length=100, unique=True)  # Unique identifier for the plasmid
    name = models.CharField(max_length=200)  # Name of the plasmid
    type = models.CharField(max_length=50)  # Type of the plasmid
    sequence = models.TextField()  # DNA sequence of the plasmid
    length = models.IntegerField()
    description = models.TextField(blank=True)
    collection = models.ForeignKey(PlasmidCollection, on_delete=models.CASCADE, related_name='plasmids')
    genbank_data = models.JSONField(blank=True, null=True)
    is_public = models.BooleanField(default=False)  # Public visibility flag

    class Meta:
        ordering = ('id', 'identifier')  # Default ordering by id and identifier
        #indexes = (('id',), ('identifier',))  # Indexes for id and identifier fields
        verbose_name = "Plasmid"  # Singular name
        verbose_name_plural = "Plasmids"  # Plural name

    def __str__(self):
        return f"{self.identifier} - {self.name}"
   

class PlasmidAnnotation(models.Model):
    plasmid = models.ForeignKey(Plasmid, on_delete=models.CASCADE, related_name='annotations')
    feature_type = models.CharField(max_length=50)  # CDS, promoter, terminator, etc.
    start = models.IntegerField()
    end = models.IntegerField()
    strand = models.IntegerField()  # 1 or -1
    label = models.CharField(max_length=200, blank=True)
    qualifiers = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.feature_type} : {self.start}-{self.end}"