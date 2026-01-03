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
    name = models

