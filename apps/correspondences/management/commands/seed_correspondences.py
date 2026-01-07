"""
This code is used to automatically seed the database with initial correspondence data for testing or development purposes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.correspondences.models import Correspondence, CorrespondenceEntry
from apps.accounts.models import User

DEMO_ENTRIES = [
    # identifier, display_name, entry_type
    ("pYTK045", "Venus", ""),
    ("pYTK046", "mCherry", ""),
    ("promoter_ACT1", "pACT1", "promoter"),
    ("terminator_ADH1", "tADH1", "terminator"),
]

class Command(BaseCommand):
    help = 'Seed a demo Correspondence + CorrespondenceEntries into the database'

    def add_arguments(self, parser):
        parser.add_argument('--owner-email', 
                            type=str, 
                            help='Email of the user who will own the correspondence'
                            )
        parser.add_argument(
            "--name",
            default="demo_correspondence",
            help="Name for the Correspondence object.",
        )
        parser.add_argument(
            "--public",
            action="store_true",
            help="Mark the correspondence as public.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing Correspondence with the same (owner, name) before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        owner_email = options['owner_email']
        name = options['name']
        is_public = options['public']
        replace = options['replace']

        try:
            owner = User.objects.get(email=owner_email)
        except User.DoesNotExist as e:
            raise CommandError(
                f"User with email '{owner_email}' does not exist. "
                f"Create a superuser or a user first."
            ) from e
        
        qs = Correspondence.objects.filter(owner=owner, name=name)
        if qs.exists() and replace:
            qs.delete()

        corr, created = Correspondence.objects.get_or_create(
            owner=owner,
            name=name,
            defaults={"is_public": is_public},
        )

        # 如果已存在且不 replace，就避免重复灌入
        if not created and not replace and corr.entries.exists():
            self.stdout.write(self.style.WARNING("Already seeded; nothing to do."))
            return

        # 更新 public 标记（如果你希望命令每次都能覆盖）
        if corr.is_public != is_public:
            corr.is_public = is_public
            corr.save(update_fields=["is_public"])

        # 简单冲突检查：同一个 identifier 在 demo 里出现多次
        seen = set()
        for identifier, display_name, entry_type in DEMO_ENTRIES:
            if identifier in seen:
                raise CommandError(f"Duplicate identifier in DEMO_ENTRIES: {identifier}")
            seen.add(identifier)

        entries = [
            CorrespondenceEntry(
                correspondence=corr,
                identifier=identifier,
                display_name=display_name,
                entry_type=entry_type or "",
            )
            for identifier, display_name, entry_type in DEMO_ENTRIES
        ]

        # bulk_create 前先清空旧 entries（如果不是新建）
        if corr.entries.exists():
            corr.entries.all().delete()

        CorrespondenceEntry.objects.bulk_create(entries)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded correspondence '{corr.name}' (owner={owner.email}, public={corr.is_public}) "
                f"with {len(entries)} entries."
            )
        )
