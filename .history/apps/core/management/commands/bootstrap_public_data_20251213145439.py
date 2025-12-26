""""
初始化网页的时候自动加载公共数据： 公共 typed 模板 Campaign_display_L1.xlsx
两套公共 plasmid collection：pYTK、pYS
并可归属于管理员账户
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser
from apps.core.utils.bootstrap import bootstrap_public_data
class Command(BaseCommand):
    help = "Bootstrap public data into the database."

    def handle(self, *args, **options):
        admin_email = "XXXX"
        try:
            admin_user = CustomUser.objects.get(email=admin_email)          