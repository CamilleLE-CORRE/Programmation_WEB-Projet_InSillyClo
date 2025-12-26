""""
Automatically load shared data during webpage initialization:
Shared typed template: Campaign_display_L1.xlsx
Two shared plasmid collections: pYTK, pYS
Can be assigned to administrator accounts only.

"""
from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser
from apps.core.utils.bootstrap import bootstrap_public_data

class Command(BaseCommand):