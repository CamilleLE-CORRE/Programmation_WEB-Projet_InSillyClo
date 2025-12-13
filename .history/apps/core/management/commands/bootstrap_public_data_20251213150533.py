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
    help = 'Bootstrap public data into the database and associate it with an admin user.'

    def add_arguments(self, parser):
        parser.add_argument('admin_email', type=str, help='Email of the administrator user to associate the data with.')

    def handle(self, *args, **kwargs):
        admin_email = kwargs['admin_email']
        try:
            admin_user = CustomUser.objects.get(email=admin_email, role='administratrice')
        except CustomUser.DoesNotExist:
            self.stderr.write(f'Error: No administrator user found with email {admin_email}.')
            return

        bootstrap_public_data(admin_user)
        self.stdout.write(self.style.SUCCESS('Successfully bootstrapped public data.'))