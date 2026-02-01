from django.db import models
from django.conf import settings

class CampaignTemplate(models.Model):
    TYPE_CHOICES = [
        ('simple', 'Simple'),
        ('typed', 'Typed'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    template_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    restriction_enzyme = models.CharField(max_length=50)
    separator = models.CharField(max_length=5, default='.')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='templates'
    )
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

