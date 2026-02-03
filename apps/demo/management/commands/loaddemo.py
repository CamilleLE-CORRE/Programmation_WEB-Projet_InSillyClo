"""
demo data loader for InSillyClo web application

⚠️ SECURITY NOTE:
All credentials defined in this file are INTENTIONALLY FAKE.
They are demo-only, non-sensitive, and safe to commit.
No real passwords, secrets, or production credentials are used here.

Usage:
  python manage.py loaddemo
  python manage.py loaddemo --skip-genbank
  python manage.py loaddemo --minimal
"""

from __future__ import annotations

import os
from datetime import timedelta

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()


# -----------------------------------------------------------------------------
# Helpers: model + fields introspection (so the command survives schema changes)
# -----------------------------------------------------------------------------
def get_model(app_label: str, model_name: str):
    try:
        return django_apps.get_model(app_label, model_name)
    except Exception:
        return None


def has_field(model, field_name: str) -> bool:
    if model is None:
        return False
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def set_if_field(obj, field_name: str, value):
    if obj is None:
        return
    if value is None:
        return
    if has_field(obj.__class__, field_name):
        setattr(obj, field_name, value)


def pick_field(model, candidates: list[str]) -> str | None:
    for c in candidates:
        if has_field(model, c):
            return c
    return None


# -----------------------------------------------------------------------------
# Command
# -----------------------------------------------------------------------------
class Command(BaseCommand):
    help = "Load demo data for InSillyClo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-genbank",
            action="store_true",
            help="Skip importing GenBank files",
        )
        parser.add_argument(
            "--minimal",
            action="store_true",
            help="Load minimal data (faster for testing)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting demo data load..."))
        self.minimal = bool(options.get("minimal", False))

        # Cache models (use installed app labels, not import paths)
        self.Team = get_model("accounts", "Team") or get_model("teams", "Team")
        self.TeamMembership = get_model("accounts", "TeamMembership") or get_model("teams", "TeamMembership")

        self.CampaignTemplate = get_model("campaigns", "CampaignTemplate")
        self.Plasmid = get_model("plasmids", "Plasmid")
        self.PlasmidCollection = get_model("plasmids", "PlasmidCollection")
        self.PlasmidAnnotation = get_model("plasmids", "PlasmidAnnotation")

        self.Correspondence = get_model("correspondences", "Correspondence")
        self.CorrespondenceEntry = get_model("correspondences", "CorrespondenceEntry")

        self.PublicationRequest = get_model("publications", "PublicationRequest")
        self.PublicationStatus = get_model("publications", "PublicationStatus")

        self.Campaign = get_model("simulations", "Campaign")
        self.CampaignResult = get_model("simulations", "CampaignResult")

        # Build data
        self.users: dict[str, object] = {}
        self.teams: dict[str, object] = {}
        self.templates: dict[str, object] = {}
        self.collections: dict[str, object] = {}
        self.plasmids: dict[str, object] = {}
        self.correspondences: dict[str, object] = {}
        self.campaigns: dict[str, object] = {}

        self.create_users()
        self.create_teams()
        self.create_campaign_templates()
        self.create_plasmid_collections()

        if not options.get("skip_genbank", False):
            self.import_genbank_files()

        self.create_demo_plasmids()
        self.create_correspondences()
        self.create_campaigns()
        self.create_publication_requests()

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("DEMO DATA LOADED SUCCESSFULLY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.print_summary()

    # =====================================================================
    # USERS
    # =====================================================================
    def create_users(self):
        self.stdout.write("\n>>> Creating users...")

        self.users = {}

        users_data = [
            # Superuser
            {
                "email": "admin@insillyclo.com",
                "password": "admin123",
                "first_name": "Admin",
                "last_name": "System",
                "is_superuser": True,
                "is_staff": True,
            },
            # Staff (team leads)
            {
                "email": "marie.dupont@insillyclo.com",
                "password": "marie123",
                "first_name": "Marie",
                "last_name": "Dupont",
                "is_staff": True,
            },
            {
                "email": "jean.martin@insillyclo.com",
                "password": "jean123",
                "first_name": "Jean",
                "last_name": "Martin",
                "is_staff": True,
            },
            {
                "email": "claire.bernard@insillyclo.com",
                "password": "claire123",
                "first_name": "Claire",
                "last_name": "Bernard",
                "is_staff": True,
            },
            # Regular users
            {
                "email": "sophie.rousseau@insillyclo.com",
                "password": "sophie123",
                "first_name": "Sophie",
                "last_name": "Rousseau",
                "is_staff": False,
            },
            {
                "email": "lucas.petit@insillyclo.com",
                "password": "lucas123",
                "first_name": "Lucas",
                "last_name": "Petit",
                "is_staff": False,
            },
            {
                "email": "emma.moreau@insillyclo.com",
                "password": "emma123",
                "first_name": "Emma",
                "last_name": "Moreau",
                "is_staff": False,
            },
            {
                "email": "thomas.leroy@insillyclo.com",
                "password": "thomas123",
                "first_name": "Thomas",
                "last_name": "Leroy",
                "is_staff": False,
            },
            {
                "email": "julie.simon@insillyclo.com",
                "password": "julie123",
                "first_name": "Julie",
                "last_name": "Simon",
                "is_staff": False,
            },
        ]

        if not self.minimal:
            users_data.extend(
                [
                    {
                        "email": "pierre.garcia@insillyclo.com",
                        "password": "pierre123",
                        "first_name": "Pierre",
                        "last_name": "Garcia",
                        "is_staff": False,
                    },
                    {
                        "email": "camille.roux@insillyclo.com",
                        "password": "camille123",
                        "first_name": "Camille",
                        "last_name": "Roux",
                        "is_staff": False,
                    },
                ]
            )

        for raw in users_data:
            data = raw.copy()

            email = data.pop("email")
            password = data.pop("password")
            is_superuser = data.pop("is_superuser", False)
            is_staff = data.pop("is_staff", False)

            user = User.objects.filter(email=email).first()
            if user:
                self.stdout.write(self.style.WARNING(f"  ⚠ User {email} already exists"))
            else:
                if is_superuser:
                    user = User.objects.create_superuser(
                        email=email,
                        password=password,
                        **data,
                    )
                else:
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        **data,
                    )

                if hasattr(user, "is_staff"):
                    user.is_staff = bool(is_staff)
                    user.save(update_fields=["is_staff"])

                self.stdout.write(self.style.SUCCESS(f"  ✓ Created {email}"))

            self.users[email] = user


    # =====================================================================
    # TEAMS
    # =====================================================================
    def create_teams(self):
        self.stdout.write("\n>>> Creating teams...")

        if self.Team is None:
            self.stdout.write(self.style.WARNING("  ⚠ Team model not found (accounts.Team or teams.Team). Skipping teams."))
            return

        teams_data = [
            {
                "name": "Équipe Synthèse Génomique",
                "owner": "marie.dupont@insillyclo.com",
                "members": [
                    "marie.dupont@insillyclo.com",
                    "sophie.rousseau@insillyclo.com",
                    "lucas.petit@insillyclo.com",
                    "thomas.leroy@insillyclo.com",
                ],
            },
            {
                "name": "Équipe Biologie Synthétique",
                "owner": "jean.martin@insillyclo.com",
                "members": [
                    "jean.martin@insillyclo.com",
                    "emma.moreau@insillyclo.com",
                    "julie.simon@insillyclo.com",
                ],
            },
            {
                "name": "Équipe Plasmides & Assemblage",
                "owner": "claire.bernard@insillyclo.com",
                "members": [
                    "claire.bernard@insillyclo.com",
                    "sophie.rousseau@insillyclo.com",
                    "emma.moreau@insillyclo.com",
                    "lucas.petit@insillyclo.com",
                ],
            },
        ]

        if not self.minimal:
            teams_data.extend(
                [
                    {
                        "name": "Équipe CRISPR-Cas9",
                        "owner": "marie.dupont@insillyclo.com",
                        "members": [
                            "marie.dupont@insillyclo.com",
                            "pierre.garcia@insillyclo.com",
                            "camille.roux@insillyclo.com",
                        ],
                    },
                    {
                        "name": "Équipe Levures Modifiées",
                        "owner": "jean.martin@insillyclo.com",
                        "members": [
                            "jean.martin@insillyclo.com",
                            "thomas.leroy@insillyclo.com",
                            "julie.simon@insillyclo.com",
                        ],
                    },
                ]
            )

        has_members_m2m = has_field(self.Team, "members")
        owner_field = pick_field(self.Team, ["owner", "created_by", "leader"])

        for data in teams_data:
            name = data["name"]
            team = self.Team.objects.filter(name=name).first()
            if team:
                self.stdout.write(self.style.WARNING(f"  ⚠ Team '{name}' already exists"))
                self.teams[name] = team
                continue

            owner = self.users[data["owner"]]
            create_kwargs = {"name": name}
            if owner_field:
                create_kwargs[owner_field] = owner

            team = self.Team.objects.create(**create_kwargs)

            # Add members
            members = [self.users[e] for e in data["members"]]
            if has_members_m2m:
                try:
                    team.members.add(*members)
                except Exception:
                    pass
            elif self.TeamMembership is not None:
                # Best-effort: create memberships
                role_field = pick_field(self.TeamMembership, ["role"])
                for u in members:
                    m = self.TeamMembership.objects.filter(team=team, user=u).first()
                    if not m:
                        kwargs = {"team": team, "user": u}
                        if role_field and u == owner:
                            kwargs[role_field] = "OWNER"
                        self.TeamMembership.objects.create(**kwargs)

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created team '{name}'"))
            self.teams[name] = team

    # =====================================================================
    # CAMPAIGN TEMPLATES
    # =====================================================================
    def create_campaign_templates(self):
        self.stdout.write("\n>>> Creating campaign templates...")

        if self.CampaignTemplate is None:
            self.stdout.write(self.style.WARNING("  ⚠ CampaignTemplate model not found. Skipping templates."))
            return

        templates_data = [
            {
                "name": "YTK Standard Assembly",
                "template_type": "typed",
                "restriction_enzyme": "BsaI",
                "separator": ".",
                "owner": "marie.dupont@insillyclo.com",
                "is_public": True,
            },
            {
                "name": "Raw BsaI Assembly",
                "template_type": "simple",
                "restriction_enzyme": "BsaI",
                "separator": "-",
                "owner": "jean.martin@insillyclo.com",
                "is_public": True,
            },
            {
                "name": "Expression Levure (BsmBI)",
                "template_type": "typed",
                "restriction_enzyme": "BsmBI",
                "separator": ".",
                "owner": "claire.bernard@insillyclo.com",
                "is_public": False,
            },
            {
                "name": "CRISPR-Cas9 Assembly",
                "template_type": "typed",
                "restriction_enzyme": "BsaI",
                "separator": "-",
                "owner": "marie.dupont@insillyclo.com",
                "is_public": False,
            },
        ]

        if not self.minimal:
            templates_data.extend(
                [
                    {
                        "name": "MoClo Level 0",
                        "template_type": "simple",
                        "restriction_enzyme": "BsaI",
                        "separator": "_",
                        "owner": "jean.martin@insillyclo.com",
                        "is_public": True,
                    },
                    {
                        "name": "Golden Gate Multi-Part",
                        "template_type": "typed",
                        "restriction_enzyme": "BsmBI",
                        "separator": ".",
                        "owner": "claire.bernard@insillyclo.com",
                        "is_public": False,
                    },
                ]
            )

        public_field = pick_field(self.CampaignTemplate, ["is_public", "public"])
        owner_field = pick_field(self.CampaignTemplate, ["owner", "created_by"])

        for data in templates_data:
            name = data["name"]
            template = self.CampaignTemplate.objects.filter(name=name).first()
            if template:
                self.stdout.write(self.style.WARNING(f"  ⚠ Template '{name}' already exists"))
                self.templates[name] = template
                continue

            owner = self.users[data.pop("owner")]
            create_kwargs = {
                "name": data["name"],
                "template_type": data.get("template_type"),
                "restriction_enzyme": data.get("restriction_enzyme"),
                "separator": data.get("separator"),
            }
            if owner_field:
                create_kwargs[owner_field] = owner
            if public_field:
                create_kwargs[public_field] = bool(data.get("is_public", False))

            # Filter only existing fields
            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.CampaignTemplate, k)}
            template = self.CampaignTemplate.objects.create(**create_kwargs)

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created template '{name}'"))
            self.templates[name] = template

    # =====================================================================
    # PLASMID COLLECTIONS
    # =====================================================================
    def create_plasmid_collections(self):
        self.stdout.write("\n>>> Creating plasmid collections...")

        if self.PlasmidCollection is None:
            self.stdout.write(self.style.WARNING("  ⚠ PlasmidCollection model not found. Skipping collections."))
            return

        public_field = pick_field(self.PlasmidCollection, ["is_public", "public"])
        owner_field = pick_field(self.PlasmidCollection, ["owner", "created_by"])
        team_field = pick_field(self.PlasmidCollection, ["team"])

        collections_data = [
            {"name": "pYTK Collection", "owner": None, "team": None, "is_public": True},
            {"name": "pYS Collection", "owner": None, "team": None, "is_public": True},
            {"name": "Équipe Synthèse - Plasmides Privés", "owner": "marie.dupont@insillyclo.com", "team": "Équipe Synthèse Génomique", "is_public": False},
            {"name": "Équipe Biologie - Collection Levure", "owner": "jean.martin@insillyclo.com", "team": "Équipe Biologie Synthétique", "is_public": False},
            {"name": "CRISPR Toolkit", "owner": "marie.dupont@insillyclo.com", "team": "Équipe Plasmides & Assemblage", "is_public": False},
            {"name": "Collection Personnelle Sophie", "owner": "sophie.rousseau@insillyclo.com", "team": None, "is_public": False},
        ]

        if not self.minimal:
            collections_data.extend(
                [
                    {"name": "pMISC Collection", "owner": None, "team": None, "is_public": True},
                    {"name": "Promoters Library", "owner": "jean.martin@insillyclo.com", "team": "Équipe Biologie Synthétique", "is_public": False},
                    {"name": "Fluorescent Reporters", "owner": "claire.bernard@insillyclo.com", "team": None, "is_public": False},
                ]
            )

        for data in collections_data:
            name = data["name"]
            obj = self.PlasmidCollection.objects.filter(name=name).first()
            if obj:
                self.stdout.write(self.style.WARNING(f"  ⚠ Collection '{name}' already exists"))
                self.collections[name] = obj
                continue

            create_kwargs = {"name": name}

            if owner_field and data["owner"]:
                create_kwargs[owner_field] = self.users[data["owner"]]

            if team_field and data["team"] and data["team"] in self.teams:
                create_kwargs[team_field] = self.teams[data["team"]]

            if public_field:
                create_kwargs[public_field] = bool(data["is_public"])

            # Filter
            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.PlasmidCollection, k)}
            obj = self.PlasmidCollection.objects.create(**create_kwargs)

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created collection '{name}'"))
            self.collections[name] = obj

    # =====================================================================
    # GENBANK IMPORT
    # =====================================================================
    def import_genbank_files(self):
        self.stdout.write("\n>>> Importing GenBank files...")

        genbank_imports = [
            ("data/pYTK", "pYTK Collection", True),
            ("data/pYS", "pYS Collection", True),
        ]
        if not self.minimal:
            genbank_imports.extend(
                [
                    ("data/pMISC", "pMISC Collection", False),
                    ("data/pMYTK", "pMYTK Collection", False),
                ]
            )

        for path, collection, is_public in genbank_imports:
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(f"  ⚠ Path {path} not found, skipping..."))
                continue

            self.stdout.write(f"  Importing {collection} from {path}...")
            try:
                if is_public:
                    call_command("import_genbank", path, collection=collection, public=True)
                else:
                    call_command("import_genbank", path, collection=collection)
                self.stdout.write(self.style.SUCCESS(f"  ✓ {collection} imported"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Import error {collection}: {e}"))
                self.stdout.write(self.style.WARNING("  ⚠ Fix import_genbank.py (must define class Command(BaseCommand))."))

    # =====================================================================
    # DEMO PLASMIDS 
    # =====================================================================
    def create_demo_plasmids(self):
        self.stdout.write("\n>>> Creating demo plasmids...")

        if self.Plasmid is None or self.PlasmidCollection is None:
            self.stdout.write(self.style.WARNING("  ⚠ Plasmid / PlasmidCollection model missing. Skipping plasmids."))
            return

        # Field mapping
        id_field = pick_field(self.Plasmid, ["identifier", "genbank_id", "accession", "name", "slug"])
        name_field = pick_field(self.Plasmid, ["name"])
        seq_field = pick_field(self.Plasmid, ["sequence", "seq"])
        length_field = pick_field(self.Plasmid, ["length", "len"])
        desc_field = pick_field(self.Plasmid, ["description"])
        type_field = pick_field(self.Plasmid, ["type", "part_type"])
        public_field = pick_field(self.Plasmid, ["is_public", "public"])
        collection_field = pick_field(self.Plasmid, ["collection", "plasmid_collection"])

        # Fake sequences
        sequences = {
            "Venus": "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTACGGCAAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACCCTCGTGACCACCTTCGGCTACGGCCTGCAGTGCTTCGCCCGCTACCCCGACCACATGAAGCAGCACGACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTCTTCAAGGACGACGGCAACTACAAGACCCGCGCCGAGGTGAAGTTCGAGGGCGACACCCTGGTGAACCGCATCGAGCTGAAGGGCATCGACTTCAAGGAGGACGGCAACATCCTGGGGCACAAGCTGGAGTACAACTACAACAGCCACAACGTCTATATCATGGCCGACAAGCAGAAGAACGGCATCAAGGTGAACTTCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCCGACCACTACCAGCAGAACACCCCCATCGGCGACGGCCCCGTGCTGCTGCCCGACAACCACTACCTGAGCTACCAGTCCGCCCTGAGCAAAGACCCCAACGAGAAGCGCGATCACATGGTCCTGCTGGAGTTCGTGACCGCCGCCGGGATCACTCTCGGCATGGACGAGCTGTACAAGTAA",
            "mCherry": "ATGGTGAGCAAGGGCGAGGAGGATAACATGGCCATCATCAAGGAGTTCATGCGCTTCAAGGTGCACATGGAGGGCTCCGTGAACGGCCACGAGTTCGAGATCGAGGGCGAGGGCGAGGGCCGCCCCTACGAGGGCACCCAGACCGCCAAGCTGAAGGTGACCAAGGGTGGCCCCCTGCCCTTCGCCTGGGACATCCTGTCCCCTCAGTTCATGTACGGCTCCAAGGCCTACGTGAAGCACCCCGCCGACATCCCCGACTACTTGAAGCTGTCCTTCCCCGAGGGCTTCAAGTGGGAGCGCGTGATGAACTTCGAGGACGGCGGCGTGGTGACCGTGACCCAGGACTCCTCCCTGCAGGACGGCGAGTTCATCTACAAGGTGAAGCTGCGCGGCACCAACTTCCCCTCCGACGGCCCCGTAATGCAGAAGAAGACCATGGGCTGGGAGGCCTCCTCCGAGCGGATGTACCCCGAGGACGGCGCCCTGAAGGGCGAGATCAAGCAGAGGCTGAAGCTGAAGGACGGCGGCCACTACGACGCTGAGGTCAAGACCACCTACAAGGCCAAGAAGCCCGTGCAGCTGCCCGGCGCCTACAACGTCAACATCAAGTTGGACATCACCTCCCACAACGAGGACTACACCATCGTGGAACAGTACGAACGCGCCGAGGGCCGCCACTCCACCGGCGGCATGGACGAGCTGTACAAGTAA",
            "AmpR": "ATGAGTATTCAACATTTCCGTGTCGCCCTTATTCCCTTTTTTGCGGCATTTTGCCTTCCTGTTTTTGCTCACCCAGAAACGCTGGTGAAAGTAAAAGATGCTGAAGATCAGTTGGGTGCACGAGTGGGTTACATCGAACTGGATCTCAACAGCGGTAAGATCCTTGAGAGTTTTCGCCCCGAAGAACGTTTTCCAATGATGAGCACTTTTAAAGTTCTGCTATGTGGCGCGGTATTATCCCGTATTGACGCCGGGCAAGAGCAACTCGGTCGCCGCATACACTATTCTCAGAATGACTTGGTTGAGTACTCACCAGTCACAGAAAAGCATCTTACGGATGGCATGACAGTAAGAGAATTATGCAGTGCTGCCATAACCATGAGTGATAACACTGCGGCCAACTTACTTCTGACAACGATCGGAGGACCGAAGGAGCTAACCGCTTTTTTGCACAACATGGGGGATCATGTAACTCGCCTTGATCGTTGGGAACCGGAGCTGAATGAAGCCATACCAAACGACGAGCGTGACACCACGATGCCTGTAGCAATGGCAACAACGTTGCGCAAACTATTAACTGGCGAACTACTTACTCTAGCTTCCCGGCAACAATTAATAGACTGGATGGAGGCGGATAAAGTTGCAGGACCACTTCTGCGCTCGGCCCTTCCGGCTGGCTGGTTTATTGCTGATAAATCTGGAGCCGGTGAGCGTGGGTCTCGCGGTATCATTGCAGCACTGGGGCCAGATGGTAAGCCCTCCCGTATCGTAGTTATCTACACGACGGGGAGTCAGGCAACTATGGATGAACGAAATAGACAGATCGCTGAGATAGGTGCCTCACTGATTAAGCATTGGTAA",
        }

        plasmids_data = [
            {
                "identifier": "pYTK003",
                "name": "Venus",
                "type": "3a",
                "sequence": sequences["Venus"],
                "collection": "pYTK Collection",
                "description": "Yellow fluorescent protein",
            },
            {
                "identifier": "pYTK008",
                "name": "mCherry",
                "type": "3b",
                "sequence": sequences["mCherry"],
                "collection": "pYTK Collection",
                "description": "Red fluorescent protein",
            },
        ]

        if not self.minimal:
            plasmids_data.extend(
                [
                    {
                        "identifier": "pSA001",
                        "name": "Venus-Expression",
                        "type": "",
                        "sequence": sequences["Venus"] + "GCATGC" * 50,
                        "collection": "Équipe Synthèse - Plasmides Privés",
                        "description": "Venus expression construct",
                    },
                    {
                        "identifier": "pBIO001",
                        "name": "GAL1-Venus",
                        "type": "TU1",
                        "sequence": "GCGGCCGC" * 20 + sequences["Venus"],
                        "collection": "Équipe Biologie - Collection Levure",
                        "description": "GAL1 promoter driving Venus",
                    },
                ]
            )

        for data in plasmids_data:
            uniq = data.get("identifier")
            coll_name = data.get("collection")

            if coll_name not in self.collections:
                self.stdout.write(self.style.WARNING(f"  ⚠ Missing collection '{coll_name}', skipping plasmid {uniq}"))
                continue

            # Lookup existing
            existing = None
            if id_field and uniq:
                existing = self.Plasmid.objects.filter(**{id_field: uniq}).first()

            if existing:
                self.stdout.write(self.style.WARNING(f"  ⚠ Plasmid {uniq} already exists"))
                self.plasmids[uniq] = existing
                continue

            create_kwargs = {}
            if id_field:
                create_kwargs[id_field] = uniq
            if name_field:
                create_kwargs[name_field] = data.get("name")
            if seq_field:
                create_kwargs[seq_field] = data.get("sequence")
            if length_field and data.get("sequence"):
                create_kwargs[length_field] = len(data["sequence"])
            if desc_field:
                create_kwargs[desc_field] = data.get("description")
            if type_field:
                create_kwargs[type_field] = data.get("type")
            if public_field:
                coll_public = None
                # Try to read is_public/public from collection
                cp = self.collections[coll_name]
                if hasattr(cp, "is_public"):
                    coll_public = getattr(cp, "is_public")
                elif hasattr(cp, "public"):
                    coll_public = getattr(cp, "public")
                create_kwargs[public_field] = bool(coll_public) if coll_public is not None else False
            if collection_field:
                create_kwargs[collection_field] = self.collections[coll_name]

            # Filter
            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.Plasmid, k)}
            plasmid = self.Plasmid.objects.create(**create_kwargs)

            # Optional annotation
            if self.PlasmidAnnotation is not None:
                label = data.get("name")
                if label in {"Venus", "mCherry"}:
                    ann_kwargs = {}
                    if has_field(self.PlasmidAnnotation, "plasmid"):
                        ann_kwargs["plasmid"] = plasmid
                    if has_field(self.PlasmidAnnotation, "feature_type"):
                        ann_kwargs["feature_type"] = "CDS"
                    if has_field(self.PlasmidAnnotation, "start"):
                        ann_kwargs["start"] = 1
                    if has_field(self.PlasmidAnnotation, "end"):
                        ann_kwargs["end"] = len(data["sequence"])
                    if has_field(self.PlasmidAnnotation, "strand"):
                        ann_kwargs["strand"] = 1
                    if has_field(self.PlasmidAnnotation, "label"):
                        ann_kwargs["label"] = label
                    if has_field(self.PlasmidAnnotation, "qualifiers"):
                        ann_kwargs["qualifiers"] = {"product": [label]}

                    # Only create if minimal fields exist
                    if ann_kwargs.get("plasmid") is not None:
                        try:
                            self.PlasmidAnnotation.objects.create(**ann_kwargs)
                        except Exception:
                            pass

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created plasmid {uniq}"))
            self.plasmids[uniq] = plasmid

    # =====================================================================
    # CORRESPONDENCES
    # =====================================================================
    def create_correspondences(self):
        self.stdout.write("\n>>> Creating correspondences...")

        if self.Correspondence is None or self.CorrespondenceEntry is None:
            self.stdout.write(self.style.WARNING("  ⚠ Correspondence models missing. Skipping correspondences."))
            return

        corr_public_field = pick_field(self.Correspondence, ["is_public", "public"])
        corr_owner_field = pick_field(self.Correspondence, ["owner", "created_by"])

        entry_type_field = pick_field(self.CorrespondenceEntry, ["entry_type", "type"])
        entry_identifier_field = pick_field(self.CorrespondenceEntry, ["identifier", "key", "name"])
        entry_display_field = pick_field(self.CorrespondenceEntry, ["display_name", "value", "label"])

        correspondences_data = [
            {
                "name": "YTK to Addgene IDs",
                "owner": "marie.dupont@insillyclo.com",
                "is_public": True,
                "entries": [
                    {"identifier": "pYTK001", "display_name": "Addgene #65141", "entry_type": "Connector"},
                    {"identifier": "pYTK002", "display_name": "Addgene #65142", "entry_type": "Promoter"},
                    {"identifier": "pYTK003", "display_name": "Addgene #65143", "entry_type": "Gene"},
                    {"identifier": "pYTK004", "display_name": "Addgene #65144", "entry_type": "Terminator"},
                ],
            },
            {
                "name": "Internal Lab Codes",
                "owner": "jean.martin@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pSA001", "display_name": "LAB-2024-001", "entry_type": "Expression"},
                    {"identifier": "pSA002", "display_name": "LAB-2024-002", "entry_type": "Expression"},
                    {"identifier": "pBIO001", "display_name": "YEAST-001", "entry_type": "Yeast"},
                ],
            },
        ]

        if not self.minimal:
            correspondences_data.append(
                {
                    "name": "Freezer Location Mapping",
                    "owner": "sophie.rousseau@insillyclo.com",
                    "is_public": False,
                    "entries": [
                        {"identifier": "pYTK001", "display_name": "Box A1, Position 1", "entry_type": ""},
                        {"identifier": "pYTK002", "display_name": "Box A1, Position 2", "entry_type": ""},
                    ],
                }
            )

        for data in correspondences_data:
            name = data["name"]
            existing = self.Correspondence.objects.filter(name=name).first()
            if existing:
                self.stdout.write(self.style.WARNING(f"  ⚠ Correspondence '{name}' already exists"))
                self.correspondences[name] = existing
                continue

            create_kwargs = {"name": name}
            if corr_owner_field:
                create_kwargs[corr_owner_field] = self.users[data["owner"]]
            if corr_public_field:
                create_kwargs[corr_public_field] = bool(data["is_public"])

            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.Correspondence, k)}
            corr = self.Correspondence.objects.create(**create_kwargs)

            # Create entries
            for entry in data["entries"]:
                e_kwargs = {"correspondence": corr}
                if entry_identifier_field:
                    e_kwargs[entry_identifier_field] = entry.get("identifier", "")
                if entry_display_field:
                    e_kwargs[entry_display_field] = entry.get("display_name", "")
                if entry_type_field:
                    e_kwargs[entry_type_field] = entry.get("entry_type", "")

                e_kwargs = {k: v for k, v in e_kwargs.items() if k == "correspondence" or has_field(self.CorrespondenceEntry, k)}
                try:
                    self.CorrespondenceEntry.objects.create(**e_kwargs)
                except Exception:
                    pass

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created correspondence '{name}' ({len(data['entries'])} entries)"))
            self.correspondences[name] = corr

    # =====================================================================
    # CAMPAIGNS 
    # =====================================================================
    def create_campaigns(self):
        self.stdout.write("\n>>> Creating campaigns...")

        if self.Campaign is None:
            self.stdout.write(self.style.WARNING("  ⚠ simulations.Campaign model not found. Skipping campaigns."))
            return
        if self.CampaignTemplate is None:
            self.stdout.write(self.style.WARNING("  ⚠ campaigns.CampaignTemplate missing. Skipping campaigns."))
            return

        owner_field = pick_field(self.Campaign, ["owner", "created_by", "user"])
        template_field = pick_field(self.Campaign, ["template", "campaign_template"])
        name_field = pick_field(self.Campaign, ["name", "title"])

        # Optional JSON-ish fields
        parameters_field = pick_field(self.Campaign, ["parameters", "params", "config"])
        results_field = pick_field(self.Campaign, ["results_data", "results", "data"])
        output_files_field = pick_field(self.Campaign, ["output_files", "files"])

        # Optional M2M names (as in your DB)
        has_collections_used = hasattr(self.Campaign, "collections_used") or has_field(self.Campaign, "collections_used")
        has_produced_plasmids = hasattr(self.Campaign, "produced_plasmids") or has_field(self.Campaign, "produced_plasmids")

        campaigns_data = [
            {
                "name": "Venus Expression Screen",
                "owner": "marie.dupont@insillyclo.com",
                "template": "YTK Standard Assembly",
                "parameters": {"restriction_enzyme": "BsaI", "output_separator": "-"},
                "results_data": {"assemblies": [{"output_id": "pIB001"}]},
                "output_files": {"xlsx": "Campaign_Venus.xlsx", "generated_at": "2024-12-15T10:30:00"},
                "collections_used": ["pYTK Collection"],
                "produced_plasmids": [],
            },
            {
                "name": "Raw Assembly Test",
                "owner": "jean.martin@insillyclo.com",
                "template": "Raw BsaI Assembly",
                "parameters": {"restriction_enzyme": "BsaI", "output_separator": "-"},
                "results_data": {"assemblies": [{"output_id": "pSA001"}]},
                "output_files": {},
                "collections_used": ["pYTK Collection", "Équipe Synthèse - Plasmides Privés"],
                "produced_plasmids": ["pSA001"],
            },
        ]

        for data in campaigns_data:
            cname = data["name"]
            if name_field:
                existing = self.Campaign.objects.filter(**{name_field: cname}).first()
            else:
                existing = self.Campaign.objects.filter(pk=-1).first()

            if existing:
                self.stdout.write(self.style.WARNING(f"  ⚠ Campaign '{cname}' already exists"))
                self.campaigns[cname] = existing
                continue

            template_name = data["template"]
            if template_name not in self.templates:
                self.stdout.write(self.style.WARNING(f"  ⚠ Missing template '{template_name}', skipping campaign '{cname}'"))
                continue

            create_kwargs = {}
            if name_field:
                create_kwargs[name_field] = cname
            if owner_field:
                create_kwargs[owner_field] = self.users[data["owner"]]
            if template_field:
                create_kwargs[template_field] = self.templates[template_name]
            if parameters_field:
                create_kwargs[parameters_field] = data.get("parameters", {})
            if results_field:
                create_kwargs[results_field] = data.get("results_data", {})
            if output_files_field:
                create_kwargs[output_files_field] = data.get("output_files", {})

            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.Campaign, k)}
            try:
                campaign = self.Campaign.objects.create(**create_kwargs)
            except TypeError as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Could not create campaign '{cname}': {e}"))
                self.stdout.write(self.style.WARNING("  ⚠ Your simulations.Campaign fields differ. Align keys with the model."))
                continue

            if has_collections_used:
                try:
                    for coll_name in data.get("collections_used", []):
                        if coll_name in self.collections:
                            campaign.collections_used.add(self.collections[coll_name])
                except Exception:
                    pass

            if has_produced_plasmids:
                try:
                    for pid in data.get("produced_plasmids", []):
                        if pid in self.plasmids:
                            campaign.produced_plasmids.add(self.plasmids[pid])
                except Exception:
                    pass

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created campaign '{cname}'"))
            self.campaigns[cname] = campaign

    # =====================================================================
    # PUBLICATION REQUESTS
    # =====================================================================
    def create_publication_requests(self):
        self.stdout.write("\n>>> Creating publication requests...")

        if self.PublicationRequest is None:
            self.stdout.write(self.style.WARNING("  ⚠ publications.PublicationRequest missing. Skipping publication requests."))
            return

        team_field = pick_field(self.PublicationRequest, ["team"])
        requested_by_field = pick_field(self.PublicationRequest, ["requested_by"])
        status_field = pick_field(self.PublicationRequest, ["status"])
        decided_by_field = pick_field(self.PublicationRequest, ["decided_by"])
        decided_at_field = pick_field(self.PublicationRequest, ["decided_at"])
        rejection_reason_field = pick_field(self.PublicationRequest, ["rejection_reason"])

        # Status values
        def status_value(key: str, fallback: str):
            ps = self.PublicationStatus
            if ps is None:
                return fallback
            try:
                return getattr(ps, key)
            except Exception:
                return fallback

        PENDING_ADMIN = status_value("PENDING_ADMIN", "PENDING_ADMIN")
        PENDING_TEAM_LEAD = status_value("PENDING_TEAM_LEAD", "PENDING_TEAM_LEAD")
        APPROVED = status_value("APPROVED", "APPROVED")
        REJECTED = status_value("REJECTED", "REJECTED")

        targets = []
        if "Collection Personnelle Sophie" in self.collections:
            targets.append(("Collection Personnelle Sophie", self.collections["Collection Personnelle Sophie"]))
        if "Internal Lab Codes" in self.correspondences:
            targets.append(("Internal Lab Codes", self.correspondences["Internal Lab Codes"]))

        if not targets:
            self.stdout.write(self.style.WARNING("  ⚠ No targets (collections/correspondences) available. Skipping publication requests."))
            return

        requests_data = [
            {
                "target": self.collections.get("Collection Personnelle Sophie"),
                "requested_by": "sophie.rousseau@insillyclo.com",
                "status": PENDING_ADMIN,
                "team": None,
            },
            {
                "target": self.collections.get("CRISPR Toolkit"),
                "requested_by": "marie.dupont@insillyclo.com",
                "status": PENDING_TEAM_LEAD,
                "team": self.teams.get("Équipe Plasmides & Assemblage"),
            },
            {
                "target": self.correspondences.get("Internal Lab Codes"),
                "requested_by": "jean.martin@insillyclo.com",
                "status": APPROVED,
                "team": None,
                "decided_by": "admin@insillyclo.com",
                "decided_at": timezone.now() - timedelta(days=5),
            },
        ]

        if not self.minimal:
            requests_data.append(
                {
                    "target": self.correspondences.get("Freezer Location Mapping"),
                    "requested_by": "sophie.rousseau@insillyclo.com",
                    "status": REJECTED,
                    "team": None,
                    "decided_by": "admin@insillyclo.com",
                    "decided_at": timezone.now() - timedelta(days=10),
                    "rejection_reason": "Information trop spécifique au laboratoire",
                }
            )

        for data in requests_data:
            target = data.get("target")
            if target is None:
                continue

            content_type = ContentType.objects.get_for_model(target)
            object_id = target.id

            # Respect unique constraint on (content_type, object_id) if present
            exists = self.PublicationRequest.objects.filter(content_type=content_type, object_id=object_id).exists()
            if exists:
                self.stdout.write(self.style.WARNING(f"  ⚠ Publication request for {target} already exists"))
                continue

            create_kwargs = {"content_type": content_type, "object_id": object_id}

            if requested_by_field:
                create_kwargs[requested_by_field] = self.users[data["requested_by"]]
            if status_field:
                create_kwargs[status_field] = data.get("status")

            if team_field and data.get("team") is not None:
                create_kwargs[team_field] = data["team"]

            if decided_by_field and data.get("decided_by"):
                create_kwargs[decided_by_field] = self.users[data["decided_by"]]
            if decided_at_field and data.get("decided_at"):
                create_kwargs[decided_at_field] = data["decided_at"]
            if rejection_reason_field and data.get("rejection_reason"):
                create_kwargs[rejection_reason_field] = data["rejection_reason"]

            create_kwargs = {k: v for k, v in create_kwargs.items() if k in {"content_type", "object_id"} or has_field(self.PublicationRequest, k)}
            try:
                pr = self.PublicationRequest.objects.create(**create_kwargs)
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created publication request for {target}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Could not create publication request for {target}: {e}"))

    # =====================================================================
    # SUMMARY
    # =====================================================================
    def print_summary(self):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\n✓ Users cached: {len(self.users)}")
        self.stdout.write(f"✓ Teams cached: {len(self.teams)}")
        self.stdout.write(f"✓ Templates cached: {len(self.templates)}")
        self.stdout.write(f"✓ Collections cached: {len(self.collections)}")
        self.stdout.write(f"✓ Plasmids cached: {len(self.plasmids)}")
        self.stdout.write(f"✓ Correspondences cached: {len(self.correspondences)}")
        self.stdout.write(f"✓ Campaigns cached: {len(self.campaigns)}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("LOGIN CREDENTIALS"))
        self.stdout.write("=" * 80)

        self.stdout.write("\nSUPERUSER:")
        self.stdout.write("  Email: admin@insillyclo.com")
        self.stdout.write("  Password: admin123")

        self.stdout.write("\nTEAM LEADS (staff):")
        self.stdout.write("  Email: marie.dupont@insillyclo.com | Password: marie123")
        self.stdout.write("  Email: jean.martin@insillyclo.com | Password: jean123")
        self.stdout.write("  Email: claire.bernard@insillyclo.com | Password: claire123")

        self.stdout.write("\nREGULAR USERS:")
        self.stdout.write("  Email: sophie.rousseau@insillyclo.com | Password: sophie123")
        self.stdout.write("  Email: lucas.petit@insillyclo.com | Password: lucas123")
        self.stdout.write("  Email: emma.moreau@insillyclo.com | Password: emma123")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Run: python manage.py runserver"))
        self.stdout.write("=" * 80 + "\n")
