"""
Management command to charge demo data for InSillyClo web application

⚠️ SECURITY NOTE:
All credentials defined in this file are INTENTIONALLY FAKE.
They are demo-only, non-sensitive, and safe to commit.
No real passwords, secrets, or production credentials are used here.

Usage: python manage.py load_demo_data
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Download demo data for InSillyClo (authorisation by email)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-genbank",
            action="store_true",
            help="Skip importing GenBank files",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting to load demo data..."))

        self.create_superuser()
        self.create_staff_users()
        self.create_regular_users()
        self.create_teams()
        self.create_templates()

        if not options["skip_genbank"]:
            self.import_genbank_files()

        self.stdout.write(self.style.SUCCESS("Demo data successfully loaded!"))
        self.print_credentials()

    # ----------------------------
    # Users (email-login)
    # ----------------------------
    def create_superuser(self):
        self.stdout.write("Creating superuser...")
        admin_email = "admin@insillyclo.com"

        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password="admin123",
                first_name="Admin",
                last_name="InSillyClo",
            )
            self.stdout.write(self.style.SUCCESS('  Superuser "admin" created'))
        else:
            self.stdout.write(self.style.WARNING('  Superuser "admin" already exists'))

    def create_staff_users(self):
        self.stdout.write("Creating staff users...")

        staff_users = [
            {
                "email": "researcher1@insillyclo.com",
                "password": "researcher123",
                "first_name": "Marie",
                "last_name": "Dupont",
                "is_staff": True,
            },
            {
                "email": "researcher2@insillyclo.com",
                "password": "researcher123",
                "first_name": "Jean",
                "last_name": "Martin",
                "is_staff": True,
            },
        ]

        for data in staff_users:
            email = data["email"]
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password=data["password"],
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                )
                if data.get("is_staff"):
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])
                self.stdout.write(self.style.SUCCESS(f'  Staff user "{email}" créé'))
            else:
                self.stdout.write(self.style.WARNING(f'  Staff user "{email}" existe déjà'))

    def create_regular_users(self):
        self.stdout.write("Creating regular users...")

        regular_users = [
            {
                "email": "user1@example.com",
                "password": "user123",
                "first_name": "Sophie",
                "last_name": "Bernard",
            },
            {
                "email": "user2@example.com",
                "password": "user123",
                "first_name": "Lucas",
                "last_name": "Petit",
            },
            {
                "email": "user3@example.com",
                "password": "user123",
                "first_name": "Emma",
                "last_name": "Rousseau",
            },
        ]

        for data in regular_users:
            email = data["email"]
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password=data["password"],
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                )
                self.stdout.write(self.style.SUCCESS(f'  Regular user "{email}" created'))
            else:
                self.stdout.write(self.style.WARNING(f'  Regular user "{email}" already exists.'))

    # ----------------------------
    # Teams / Templates
    # -----------------------------
    def create_teams(self):
        self.stdout.write("Creating teams...")

        try:
            from apps.teams.models import Team
        except Exception:
            try:
                from teams.models import Team
            except ImportError:
                self.stdout.write(self.style.WARNING("  Team model not found, skipping..."))
                return

        teams_data = [
            {
                "name": "Équipe Synthèse Génomique",
                "owner_email": "researcher1@insillyclo.com",
                "members": ["researcher1@insillyclo.com", "user1@example.com", "user2@example.com"],
            },
            {
                "name": "Équipe Biologie Synthétique",
                "owner_email": "researcher2@insillyclo.com",
                "members": ["researcher2@insillyclo.com", "user3@example.com"],
            },
            {
                "name": "Équipe Plasmides",
                "owner_email": "researcher1@insillyclo.com",
                "members": ["researcher1@insillyclo.com", "researcher2@insillyclo.com", "user1@example.com"],
            },
        ]

        for team_data in teams_data:
            team_name = team_data["name"]

            if Team.objects.filter(name=team_name).exists():
                self.stdout.write(self.style.WARNING(f'  Team "{team_name}" already exists'))
                continue

            owner = User.objects.get(email=team_data["owner_email"])
            members_emails = team_data["members"]

            team = Team.objects.create(
                name=team_name,
                owner=owner,
            )

            for email in members_emails:
                user = User.objects.get(email=email)
                team.members.add(user)

            self.stdout.write(self.style.SUCCESS(f'  ✓ Team "{team_name}" created'))


    def create_templates(self):
        self.stdout.write("Creating templates...")

        try:
            from apps.campaigns.models import CampaignTemplate
        except Exception:
            try:
                from campaigns.models import CampaignTemplate
            except ImportError:
                self.stdout.write(self.style.WARNING("  Model CampaignTemplate not found, skipping..."))
                return

        templates_data = [
            {
                "name": "Template YTK Standard",
                "template_type": "simple",
                "restriction_enzyme": "BsaI",
                "separator": ".",
                "owner_email": "researcher1@insillyclo.com",
            },
            {
                "name": "Template Expression Levure",
                "template_type": "typed",
                "restriction_enzyme": "BsmBI",
                "separator": ".",
                "owner_email": "researcher2@insillyclo.com",
            },
            {
                "name": "Template CRISPR-Cas9",
                "template_type": "typed",
                "restriction_enzyme": "BsaI",
                "separator": "-",
                "owner_email": "researcher1@insillyclo.com",
            },
        ]

        for data in templates_data:
            name = data["name"]

            if CampaignTemplate.objects.filter(name=name).exists():
                self.stdout.write(self.style.WARNING(f'  ⚠ Template "{name}" already exists'))
                continue

            owner_email = data.pop("owner_email")
            data["owner"] = User.objects.get(email=owner_email)

            CampaignTemplate.objects.create(**data)
            self.stdout.write(self.style.SUCCESS(f'  Template "{name}" créé'))


    # ----------------------------
    # GenBank import
    # ----------------------------
    def import_genbank_files(self):
        self.stdout.write("Importing GenBank files...")

        genbank_imports = [
            ("data/pYTK", "pYTK Collection", True),
            ("data/pYS", "pYS Collection", True),
            ("data/pMISC", "pMISC Collection", False),
            ("data/pMYTK", "pMYTK Collection", False),
        ]

        from django.core.management import call_command

        for path, collection, is_public in genbank_imports:
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(f"  Path {path} not found, skipping..."))
                continue

            self.stdout.write(f"  Importing {collection} from {path}...")
            try:
                if is_public:
                    call_command("import_genbank", path, collection=collection, public=True)
                else:
                    call_command("import_genbank", path, collection=collection)
                self.stdout.write(self.style.SUCCESS(f"  {collection} importée"))
            except TypeError:
                # Fallback to string args
                args = [path, f"--collection={collection}"]
                if is_public:
                    args.append("--public")
                call_command("import_genbank", *args)
                self.stdout.write(self.style.SUCCESS(f"  {collection} imported"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Import error {collection}: {e}"))

    # ----------------------------
    # Output
    # ----------------------------
    def print_credentials(self):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("CONNEXION CREDENTIALS (login par email)"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nSUPERUSER:")
        self.stdout.write("  Email: admin@insillyclo.com")
        self.stdout.write("  Password: admin123")

        self.stdout.write("\nSTAFF USERS:")
        self.stdout.write("  Email: researcher1@insillyclo.com | Password: researcher123")
        self.stdout.write("  Email: researcher2@insillyclo.com | Password: researcher123")

        self.stdout.write("\nREGULAR USERS:")
        self.stdout.write("  Email: user1@example.com | Password: user123")
        self.stdout.write("  Email: user2@example.com | Password: user123")
        self.stdout.write("  Email: user3@example.com | Password: user123")

        self.stdout.write("=" * 60 + "\n")

        self.stdout.write(self.style.SUCCESS("Demo data succesfully imported!"))
        self.stdout.write(self.style.SUCCESS("Run python manage.py runserver to start the development server."))
