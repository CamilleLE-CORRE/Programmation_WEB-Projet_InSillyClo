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

