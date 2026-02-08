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
import random
from datetime import timedelta

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.exceptions import FieldDoesNotExist
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

        self.Publication = get_model("publications", "Publication")
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

        # NEW: ensure staff have permissions in Django admin
        self.setup_staff_admin_permissions()

        self.create_teams()
        self.create_campaign_templates()
        self.create_plasmid_collections()

        # Optional: import existing GenBank libraries if your import command fills genbank_data["features"].
        if not options.get("skip_genbank", False):
            self.import_genbank_files()

        # Create realistic plasmids even without GenBank import (annotations-driven visual map).
        self.create_demo_plasmids()

        self.create_correspondences()
        self.create_campaigns()
        self.create_publication_requests()

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("DEMO DATA LOADED SUCCESSFULLY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.print_summary()

    # =====================================================================
    # STAFF PERMISSIONS (Django admin)
    # =====================================================================
    def setup_staff_admin_permissions(self):
        """
        Creates a Group "Administratrices" and grants it view/change permissions
        on campaigns.CampaignTemplate, then attaches all is_staff users to it.
        """
        self.stdout.write("\n>>> Setting up staff permissions (Django admin)...")

        if self.CampaignTemplate is None:
            self.stdout.write(self.style.WARNING("  ⚠ CampaignTemplate model not found. Skipping staff permissions."))
            return

        admin_group, _ = Group.objects.get_or_create(name="Administratrices")

        ct = ContentType.objects.get_for_model(self.CampaignTemplate)
        needed_codenames = ["view_campaigntemplate", "change_campaigntemplate"]

        perms = Permission.objects.filter(content_type=ct, codename__in=needed_codenames)
        found = set(perms.values_list("codename", flat=True))
        missing = [c for c in needed_codenames if c not in found]
        if missing:
            self.stdout.write(self.style.WARNING(f"  ⚠ Missing permissions in DB: {missing}."))
            self.stdout.write(self.style.WARNING("    Run migrations, ensure ContentType/Permission are created."))
        else:
            admin_group.permissions.add(*perms)

        # Attach all staff users (excluding superuser is optional; keeping it is harmless)
        staff_users = User.objects.filter(is_staff=True)
        for u in staff_users:
            u.groups.add(admin_group)

        self.stdout.write(self.style.SUCCESS(f"  ✓ Group 'Administratrices' ready ({staff_users.count()} staff users attached)"))

    # =====================================================================
    # DNA + annotation helpers (to get a realistic plasmid map)
    # =====================================================================
    def _dna(self, n: int) -> str:
        return "".join(random.choice("ACGT") for _ in range(int(n)))

    def _mk_plasmid_seq(self, backbone_len: int = 2600, insert_len: int = 900) -> str:
        # "Plausible" plasmid: backbone + insert (no external dependencies)
        return self._dna(backbone_len) + self._dna(insert_len)

    def add_annotation(self, plasmid, feature_type, start, end, label=None, strand=1, qualifiers=None):
        if self.PlasmidAnnotation is None:
            return
        seq_len = len(plasmid.sequence or "")
        start = max(0, int(start))
        end = min(seq_len, int(end))
        if end <= start:
            return

        try:
            self.PlasmidAnnotation.objects.create(
                plasmid=plasmid,
                feature_type=feature_type,     # promoter / RBS / CDS / terminator / rep_origin, etc.
                start=start,                   # 0-based (the view will convert as needed)
                end=end,
                strand=int(strand),
                label=(label or feature_type),
                qualifiers=qualifiers or {},
            )
        except Exception:
            pass

    def annotate_expression_plasmid(self, plasmid, gene_label: str):
        """
        Creates multi-block annotations so plasmid_detail displays a readable circular map.
        """
        L = len(plasmid.sequence or "")
        if L < 1200:
            return

        # ori
        self.add_annotation(plasmid, "rep_origin", 0, 220, "ori")

        # marker (ampR)
        m1 = int(L * 0.35)
        m2 = min(m1 + 750, L - 400)
        self.add_annotation(plasmid, "CDS", m1, m2, "ampR", qualifiers={"product": ["beta-lactamase"]})

        # expression cassette
        p1, p2 = int(L * 0.55), int(L * 0.60)
        self.add_annotation(plasmid, "promoter", p1, p2, "pTEF1")
        self.add_annotation(plasmid, "RBS", p2, p2 + 35, "RBS")

        cds1 = p2 + 35
        cds2 = min(cds1 + 720, L - 260)
        self.add_annotation(plasmid, "CDS", cds1, cds2, gene_label, qualifiers={"product": [gene_label]})

        self.add_annotation(plasmid, "terminator", max(L - 220, cds2 + 1), L, "tCYC1")

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
            # Staff
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
                    {
                        "email": "antoine.martin@insillyclo.com",
                        "password": "antoine123",
                        "first_name": "Antoine",
                        "last_name": "Martin",
                        "is_staff": False,
                    },
                    {
                        "email": "clara.dubois@insillyclo.com",
                        "password": "clara123",
                        "first_name": "Clara",
                        "last_name": "Dubois",
                        "is_staff": False,
                    },
                    {
                        "email": "nicolas.bernard@insillyclo.com",
                        "password": "nicolas123",
                        "first_name": "Nicolas",
                        "last_name": "Bernard",
                        "is_staff": False,
                    },
                    {
                        "email": "lea.fournier@insillyclo.com",
                        "password": "lea123",
                        "first_name": "Léa",
                        "last_name": "Fournier",
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
                # Ensure username uniqueness if the field exists
                if has_field(User, "username") and "username" not in data:
                    base = email.split("@")[0]
                    username = base
                    i = 1
                    while User.objects.filter(username=username).exists():
                        i += 1
                        username = f"{base}{i}"
                    data["username"] = username

                if is_superuser:
                    user = User.objects.create_superuser(email=email, password=password, **data)
                else:
                    user = User.objects.create_user(email=email, password=password, **data)

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
            # --- Mixed owners (staff + non-staff) ---
            {
                "name": "Équipe Synthèse Génomique",
                "owner": "marie.dupont@insillyclo.com",  # staff
                "members": [
                    "marie.dupont@insillyclo.com",
                    "sophie.rousseau@insillyclo.com",
                    "lucas.petit@insillyclo.com",
                    "thomas.leroy@insillyclo.com",
                    "clara.dubois@insillyclo.com",
                ],
            },
            {
                "name": "Équipe Biologie Synthétique",
                "owner": "sophie.rousseau@insillyclo.com",  # non-staff
                "members": [
                    "sophie.rousseau@insillyclo.com",
                    "emma.moreau@insillyclo.com",
                    "julie.simon@insillyclo.com",
                    "antoine.martin@insillyclo.com",
                ],
            },
            {
                "name": "Équipe Plasmides & Assemblage",
                "owner": "claire.bernard@insillyclo.com",  # staff
                "members": [
                    "claire.bernard@insillyclo.com",
                    "lucas.petit@insillyclo.com",
                    "emma.moreau@insillyclo.com",
                    "nicolas.bernard@insillyclo.com",
                ],
            },
            {
                "name": "Équipe Design & Documentation",
                "owner": "lea.fournier@insillyclo.com",  # non-staff
                "members": [
                    "lea.fournier@insillyclo.com",
                    "julie.simon@insillyclo.com",
                    "clara.dubois@insillyclo.com",
                    "antoine.martin@insillyclo.com",
                ],
            },
            {
                "name": "Équipe QA / Validation",
                "owner": "jean.martin@insillyclo.com",  # staff
                "members": [
                    "jean.martin@insillyclo.com",
                    "thomas.leroy@insillyclo.com",
                    "nicolas.bernard@insillyclo.com",
                    "lucas.petit@insillyclo.com",
                ],
            },
        ]

        if not self.minimal:
            teams_data.extend([
                {
                    "name": "Équipe CRISPR-Cas9",
                    "owner": "emma.moreau@insillyclo.com",  # non-staff
                    "members": [
                        "emma.moreau@insillyclo.com",
                        "pierre.garcia@insillyclo.com",
                        "camille.roux@insillyclo.com",
                        "marie.dupont@insillyclo.com",
                    ],
                },
                {
                    "name": "Équipe Levures Modifiées",
                    "owner": "jean.martin@insillyclo.com",  # staff
                    "members": [
                        "jean.martin@insillyclo.com",
                        "thomas.leroy@insillyclo.com",
                        "julie.simon@insillyclo.com",
                        "lea.fournier@insillyclo.com",
                    ],
                },
                {
                    "name": "Équipe Métabolisme & Pathways",
                    "owner": "antoine.martin@insillyclo.com",  # non-staff
                    "members": [
                        "antoine.martin@insillyclo.com",
                        "claire.bernard@insillyclo.com",
                        "lucas.petit@insillyclo.com",
                        "pierre.garcia@insillyclo.com",
                    ],
                },
                {
                    "name": "Équipe Bioinformatique",
                    "owner": "clara.dubois@insillyclo.com",  # non-staff
                    "members": [
                        "clara.dubois@insillyclo.com",
                        "nicolas.bernard@insillyclo.com",
                        "camille.roux@insillyclo.com",
                        "jean.martin@insillyclo.com",
                    ],
                },
            ])

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

            owner = self.users[data["owner"]]
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

        owner_field = pick_field(self.PlasmidCollection, ["owner", "created_by"])
        team_field = pick_field(self.PlasmidCollection, ["team"])
        public_field = pick_field(self.PlasmidCollection, ["is_public", "public"])

        collections_data = [
            # Public (guest sees them)
            {"name": "pYTK Public Library", "owner": None, "team": None, "is_public": True},
            {"name": "Yeast Toolkit Public", "owner": None, "team": None, "is_public": True},

            # Private team collections
            {"name": "Team Synthèse - Private", "owner": "marie.dupont@insillyclo.com", "team": "Équipe Synthèse Génomique", "is_public": False},
            {"name": "Team BioSyn - Private", "owner": "jean.martin@insillyclo.com", "team": "Équipe Biologie Synthétique", "is_public": False},

            # Private personal
            {"name": "Sophie - Personal", "owner": "sophie.rousseau@insillyclo.com", "team": None, "is_public": False},
        ]

        if not self.minimal:
            collections_data.append(
                {"name": "Plasmid Assembly - Sandbox", "owner": "claire.bernard@insillyclo.com", "team": "Équipe Plasmides & Assemblage", "is_public": False}
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
                create_kwargs[owner_field] = self.users.get(data["owner"])
            if team_field and data["team"]:
                t = self.teams.get(data["team"])
                if t:
                    create_kwargs[team_field] = t
            if public_field:
                create_kwargs[public_field] = bool(data["is_public"])

            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.PlasmidCollection, k)}
            obj = self.PlasmidCollection.objects.create(**create_kwargs)

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created collection '{name}'"))
            self.collections[name] = obj

    # =====================================================================
    # GENBANK IMPORT (optional)
    # =====================================================================
    def import_genbank_files(self):
        self.stdout.write("\n>>> Importing GenBank files...")

        genbank_imports = [
            ("data/pYTK", "pYTK Public Library", True),
            ("data/pYS", "Yeast Toolkit Public", True),
        ]

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
                self.stdout.write(self.style.WARNING("  ⚠ import_genbank command failed; demo will still work via annotations."))

    # =====================================================================
    # DEMO PLASMIDS
    # =====================================================================
    def create_demo_plasmids(self):
        self.stdout.write("\n>>> Creating demo plasmids...")

        if self.Plasmid is None or self.PlasmidCollection is None:
            self.stdout.write(self.style.WARNING("  ⚠ Plasmid / PlasmidCollection model missing. Skipping plasmids."))
            return

        # If schema differs, pick_field can be used; here we assume standard fields exist.
        id_field = pick_field(self.Plasmid, ["identifier"])
        name_field = pick_field(self.Plasmid, ["name"])
        seq_field = pick_field(self.Plasmid, ["sequence", "seq"])
        length_field = pick_field(self.Plasmid, ["length", "len"])
        desc_field = pick_field(self.Plasmid, ["description"])
        type_field = pick_field(self.Plasmid, ["type", "plasmid_type", "part_type"])
        public_field = pick_field(self.Plasmid, ["is_public", "public"])
        collection_field = pick_field(self.Plasmid, ["collection", "plasmid_collection", "plasmidCollection"])

        plasmids_data = [
            {"identifier": "pYTK008", "name": "mCherry", "type": "3b", "collection": "pYTK Public Library", "desc": "RFP reporter cassette"},
            {"identifier": "pYTK100", "name": "GFP", "type": "3a", "collection": "Yeast Toolkit Public", "desc": "GFP reporter cassette"},
            {"identifier": "pSR001", "name": "Sophie-TagTest", "type": "misc", "collection": "Sophie - Personal", "desc": "Personal test plasmid"},
            {"identifier": "pSR002", "name": "Tag-Linker-Test",        "type": "misc", "collection": "Sophie - Personal",               "desc": "Flexible linker length comparison"},
            {"identifier": "pSR003", "name": "FLAG-HA-Swap",          "type": "misc", "collection": "Sophie - Personal",               "desc": "Epitope tag replacement construct"},
            {"identifier": "pSR004", "name": "NLS-Screen",            "type": "misc", "collection": "Team Synthèse - Private",           "desc": "Nuclear localization signal screening"},
            {"identifier": "pSR005", "name": "NES-Export-Test",       "type": "misc", "collection": "Team Synthèse - Private",           "desc": "Nuclear export signal validation"},
            {"identifier": "pSR006", "name": "GFP-Fusion-Test",       "type": "misc", "collection": "Team BioSyn - Private",             "desc": "GFP fusion for subcellular localization"},
            {"identifier": "pSR007", "name": "Promoter-Strength-Test","type": "misc", "collection": "Team BioSyn - Private",             "desc": "Relative promoter activity assay"},
            {"identifier": "pSR008", "name": "Terminator-Variant-A",  "type": "misc", "collection": "Team BioSyn - Private",             "desc": "Terminator efficiency comparison"},
            {"identifier": "pSR009", "name": "MCS-Variant-Short",     "type": "misc", "collection": "Team BioSyn - Private",             "desc": "Alternative short multiple cloning site"},
            {"identifier": "pSR010", "name": "Reporter-Control-ON",   "type": "misc", "collection": "pYTK Public Library",               "desc": "Positive control reporter plasmid"},
            {"identifier": "pSR011", "name": "Reporter-Control-OFF",  "type": "misc", "collection": "pYTK Public Library",               "desc": "Negative control reporter plasmid"},
            {"identifier": "pSR012", "name": "Domain-Deletion-Test",  "type": "misc", "collection": "Sophie - Personal",                "desc": "Protein domain deletion mutant"},
            {"identifier": "pSR013", "name": "Orientation-Switch",    "type": "misc", "collection": "Team Synthèse - Private",           "desc": "Insert orientation inversion test"},
            {"identifier": "pSR014", "name": "Spacer-Length-Test",    "type": "misc", "collection": "Team Synthèse - Private",           "desc": "Inter-part spacer length evaluation"},
            {"identifier": "pSR015", "name": "Low-Copy-Backbone",     "type": "misc", "collection": "Yeast Toolkit Public",             "desc": "Low copy number backbone test"},
            {"identifier": "pSR016", "name": "High-Copy-Backbone",    "type": "misc", "collection": "Yeast Toolkit Public",             "desc": "High copy number backbone control"},
            {"identifier": "pSR017", "name": "Inducible-System-Test", "type": "misc", "collection": "Team BioSyn - Private",             "desc": "Inducible expression system validation"},
            {"identifier": "pSR018", "name": "StopCodon-Readthrough", "type": "misc", "collection": "Sophie - Personal",                "desc": "Stop codon readthrough assessment"},
            {"identifier": "pSR019", "name": "Codon-Usage-Test",      "type": "misc", "collection": "Team BioSyn - Private",             "desc": "Codon optimization comparison"},
            {"identifier": "pSR020", "name": "Minimal-Backbone",      "type": "misc", "collection": "pYTK Public Library",              "desc": "Minimal backbone construct"},
        ]

        for d in plasmids_data:
            coll_name = d["collection"]
            if coll_name not in self.collections:
                self.stdout.write(self.style.WARNING(f"  ⚠ Missing collection '{coll_name}', skip {d['identifier']}"))
                continue

            uniq = d.get("identifier")
            existing = None
            if id_field and uniq:
                existing = self.Plasmid.objects.filter(**{id_field: uniq}).first()

            if existing:
                self.stdout.write(self.style.WARNING(f"  ⚠ Plasmid {uniq} already exists"))
                self.plasmids[uniq] = existing
                continue

            seq = self._mk_plasmid_seq()

            create_kwargs = {}
            if id_field:
                create_kwargs[id_field] = uniq
            if name_field:
                create_kwargs[name_field] = d.get("name")
            if type_field:
                create_kwargs[type_field] = d.get("type", "")
            if seq_field:
                create_kwargs[seq_field] = seq
            if length_field:
                create_kwargs[length_field] = len(seq)
            if desc_field:
                create_kwargs[desc_field] = d.get("desc", "")

            if collection_field:
                create_kwargs[collection_field] = self.collections[coll_name]

            if public_field:
                coll_obj = self.collections[coll_name]
                coll_public = getattr(coll_obj, "is_public", None)
                if coll_public is None:
                    coll_public = getattr(coll_obj, "public", None)
                create_kwargs[public_field] = bool(coll_public) if coll_public is not None else False

            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.Plasmid, k)}
            plasmid = self.Plasmid.objects.create(**create_kwargs)

            # Ensure readable plasmid map even without GenBank import
            self.annotate_expression_plasmid(plasmid, d.get("name") or uniq)

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
            # =========================
            # Public
            # =========================
            {
                "name": "YTK to Addgene IDs",
                "owner": "marie.dupont@insillyclo.com",
                "is_public": True,
                "entries": [
                    {"identifier": "pYTK001", "display_name": "Addgene #65141", "entry_type": "Connector"},
                    {"identifier": "pYTK002", "display_name": "Addgene #65142", "entry_type": "Promoter"},
                    {"identifier": "pYTK003", "display_name": "Addgene #65143", "entry_type": "Gene"},
                    {"identifier": "pYTK004", "display_name": "Addgene #65144", "entry_type": "Terminator"},
                    {"identifier": "pYTK008", "display_name": "Addgene #65148", "entry_type": "Reporter"},
                ],
            },
            {
                "name": "Public Part Categories",
                "owner": "claire.bernard@insillyclo.com",
                "is_public": True,
                "entries": [
                    {"identifier": "pYTK002", "display_name": "Promoter parts", "entry_type": "Category"},
                    {"identifier": "pYTK003", "display_name": "Coding sequences", "entry_type": "Category"},
                    {"identifier": "pYTK004", "display_name": "Terminators", "entry_type": "Category"},
                    {"identifier": "pYTK008", "display_name": "Fluorescent reporters", "entry_type": "Category"},
                ],
            },
            {
                "name": "Yeast Reporters (Display Names)",
                "owner": "jean.martin@insillyclo.com",
                "is_public": True,
                "entries": [
                    {"identifier": "pYTK100", "display_name": "GFP (green fluorescent protein)", "entry_type": "Reporter"},
                    {"identifier": "pYTK008", "display_name": "mCherry (red fluorescent protein)", "entry_type": "Reporter"},
                    {"identifier": "pSR010", "display_name": "Reporter control (ON)", "entry_type": "Control"},
                    {"identifier": "pSR011", "display_name": "Reporter control (OFF)", "entry_type": "Control"},
                ],
            },

            # =========================
            # Private lab internal
            # =========================
            {
                "name": "Internal Lab Codes",
                "owner": "jean.martin@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pSA001", "display_name": "LAB-2024-001", "entry_type": "Expression"},
                    {"identifier": "pSA002", "display_name": "LAB-2024-002", "entry_type": "Expression"},
                    {"identifier": "pBIO001", "display_name": "YEAST-001", "entry_type": "Yeast"},
                    {"identifier": "pSR004", "display_name": "LAB-2025-014", "entry_type": "Screen"},
                ],
            },
            {
                "name": "Project Aliases (Short Names)",
                "owner": "marie.dupont@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pSR004", "display_name": "NLS-screen-v1", "entry_type": "Alias"},
                    {"identifier": "pSR005", "display_name": "NES-export-v1", "entry_type": "Alias"},
                    {"identifier": "pSR006", "display_name": "GFP-fusion-v2", "entry_type": "Alias"},
                    {"identifier": "pSR017", "display_name": "Inducible-test", "entry_type": "Alias"},
                ],
            },

            # =========================
            # Personal (non-public)
            # =========================
            {
                "name": "Freezer Location Mapping",
                "owner": "sophie.rousseau@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pYTK003", "display_name": "Freezer A / Box 1 / Pos 3", "entry_type": "Stock"},
                    {"identifier": "pYTK008", "display_name": "Freezer A / Box 1 / Pos 8", "entry_type": "Stock"},
                    {"identifier": "pSR001", "display_name": "Freezer B / Box 2 / Pos 1", "entry_type": "Stock"},
                ],
            },
            {
                "name": "Sophie Notes (Readable Names)",
                "owner": "sophie.rousseau@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pSR001", "display_name": "Tag test plasmid", "entry_type": "Note"},
                    {"identifier": "pSR002", "display_name": "Linker length comparison", "entry_type": "Note"},
                    {"identifier": "pSR012", "display_name": "Domain deletion mutant", "entry_type": "Note"},
                    {"identifier": "pSR018", "display_name": "Stop codon readthrough assay", "entry_type": "Note"},
                ],
            },
            {
                "name": "Lucas Bench IDs",
                "owner": "lucas.petit@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pSR013", "display_name": "BENCH-LP-001", "entry_type": "Bench"},
                    {"identifier": "pSR014", "display_name": "BENCH-LP-002", "entry_type": "Bench"},
                    {"identifier": "pSR019", "display_name": "BENCH-LP-003", "entry_type": "Bench"},
                ],
            },
            {
                "name": "Emma Strains / Plasmids Mapping",
                "owner": "emma.moreau@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "pBIO001", "display_name": "Strain EM-YEAST-01", "entry_type": "Strain"},
                    {"identifier": "pSR006", "display_name": "Strain EM-YEAST-02", "entry_type": "Strain"},
                    {"identifier": "pSR017", "display_name": "Strain EM-YEAST-03", "entry_type": "Strain"},
                ],
            },

            # =========================
            # Extra demo variety
            # =========================
            {
                "name": "Plate Layout (96-well) - Week 12",
                "owner": "julie.simon@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "A01", "display_name": "pYTK100", "entry_type": "Well"},
                    {"identifier": "A02", "display_name": "pYTK008", "entry_type": "Well"},
                    {"identifier": "B01", "display_name": "pSR010", "entry_type": "Well"},
                    {"identifier": "B02", "display_name": "pSR011", "entry_type": "Well"},
                    {"identifier": "C01", "display_name": "pSR017", "entry_type": "Well"},
                ],
            },
            {
                "name": "Primer Set Mapping",
                "owner": "claire.bernard@insillyclo.com",
                "is_public": False,
                "entries": [
                    {"identifier": "PR_FWD_01", "display_name": "pTEF1_Fwd", "entry_type": "Primer"},
                    {"identifier": "PR_REV_01", "display_name": "tCYC1_Rev", "entry_type": "Primer"},
                    {"identifier": "PR_FWD_02", "display_name": "GAL1_Fwd", "entry_type": "Primer"},
                    {"identifier": "PR_REV_02", "display_name": "ADH1_Rev", "entry_type": "Primer"},
                ],
            },
        ]

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

        parameters_field = pick_field(self.Campaign, ["parameters", "params", "config"])
        results_field = pick_field(self.Campaign, ["results_data", "results", "data"])
        output_files_field = pick_field(self.Campaign, ["output_files", "files"])

        has_collections_used = has_field(self.Campaign, "collections_used")
        has_produced_plasmids = has_field(self.Campaign, "produced_plasmids")

        campaigns_data = [
            {
                "name": "Fluorescent reporter assembly",
                "owner": "marie.dupont@insillyclo.com",
                "template": "YTK Standard Assembly",
                "parameters": {"restriction_enzyme": "BsaI", "output_separator": "-"},
                "results_data": {"assemblies": [{"output_id": "pSA001"}]},
                "output_files": {"xlsx": "Fluo_Assembly.xlsx"},
                "collections_used": ["pYTK Public Library"],
                "produced_plasmids": ["pSA001"],
            },
            {
                "name": "Yeast promoter swap",
                "owner": "jean.martin@insillyclo.com",
                "template": "Raw BsaI Assembly",
                "parameters": {"restriction_enzyme": "BsaI"},
                "results_data": {"assemblies": [{"output_id": "pBIO001"}]},
                "output_files": {},
                "collections_used": ["Yeast Toolkit Public"],
                "produced_plasmids": ["pBIO001"],
            },
        ]

        for data in campaigns_data:
            cname = data["name"]
            existing = None
            if name_field:
                existing = self.Campaign.objects.filter(**{name_field: cname}).first()

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

            # IMPORTANT: Campaign.template FK may not target campaigns.CampaignTemplate.
            if template_field:
                expected_model = self.Campaign._meta.get_field(template_field).remote_field.model
                src = self.templates[template_name]

                dst = None
                if has_field(expected_model, "name") and hasattr(src, "name"):
                    try:
                        dst = expected_model.objects.filter(name=src.name).first()
                    except Exception:
                        dst = None

                if dst is None:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ Campaign.template expects {expected_model._meta.label}; no matching template '{getattr(src,'name',template_name)}' -> skipping '{cname}'"
                    ))
                    continue

                create_kwargs[template_field] = dst

            if parameters_field:
                create_kwargs[parameters_field] = data.get("parameters", {})
            if results_field:
                create_kwargs[results_field] = data.get("results_data", {})
            if output_files_field:
                create_kwargs[output_files_field] = data.get("output_files", {})

            create_kwargs = {k: v for k, v in create_kwargs.items() if has_field(self.Campaign, k)}
            try:
                campaign = self.Campaign.objects.create(**create_kwargs)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Could not create campaign '{cname}': {e}"))
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

    def create_publication_requests(self):
        self.stdout.write("\n>>> Creating publication requests...")

        if self.Publication is None:
            self.stdout.write(self.style.WARNING(
                "  ⚠ publications.Publication model not available. Skipping publication requests."
            ))
            return

        # Build targets list (existing objects only)
        targets = []
        for _, coll in (self.collections or {}).items():
            if coll is not None:
                targets.append(coll)
        for _, corr in (self.correspondences or {}).items():
            if corr is not None:
                targets.append(corr)

        if not targets:
            self.stdout.write(self.style.WARNING("  ⚠ No valid targets for publication requests."))
            return

        # Helper: safe get status enum (in case Status enum name differs)
        Status = getattr(self.Publication, "Status", None) or getattr(self.Publication, "Statuses", None)

        if Status is None:
            self.stdout.write(self.style.WARNING("  ⚠ Publication.Status enum not found. Skipping publication requests."))
            return

        # Helper: detect if Publication model actually has a "team" FK
        def publication_has_field(field_name: str) -> bool:
            try:
                self.Publication._meta.get_field(field_name)
                return True
            except FieldDoesNotExist:
                return False
            except Exception:
                return False

        has_team_field = publication_has_field("team")

        # ------------------------------------------------------------------
        # DEMO REQUESTS
        # ------------------------------------------------------------------
        # Rules implemented:
        # - Requests with team -> often start PENDING_CHEFFE (some rejected by cheffe, some advance to PENDING_ADMIN)
        # - Requests without team -> start directly PENDING_ADMIN
        # - Some rejected (cheffe/admin) with mandatory comment
        # - Some approved (cheffe + admin)
        demo_requests = [
            # =========================================================
            # HORS ÉQUIPE → DIRECT PENDING_ADMIN
            # =========================================================
            {
                "target": self.correspondences.get("Freezer Location Mapping"),
                "requested_by": "sophie.rousseau@insillyclo.com",
                "status": Status.PENDING_ADMIN,
                "team": None,
            },
            {
                "target": self.collections.get("pYTK Public Library"),
                "requested_by": "lucas.petit@insillyclo.com",
                "status": Status.PENDING_ADMIN,
                "team": None,
            },

            # =========================================================
            # AVEC ÉQUIPE → PENDING_CHEFFE
            # =========================================================
            {
                "target": self.collections.get("Team Synthèse - Private"),
                "requested_by": "sophie.rousseau@insillyclo.com",
                "status": Status.PENDING_CHEFFE,
                "team": self.teams.get("Équipe Synthèse Génomique"),
            },
            {
                "target": self.correspondences.get("Internal Lab Codes"),
                "requested_by": "thomas.leroy@insillyclo.com",
                "status": Status.PENDING_CHEFFE,
                "team": self.teams.get("Équipe Biologie Synthétique"),
            },

            # =========================================================
            # VALIDÉE PAR CHEFFE → PENDING_ADMIN
            # =========================================================
            {
                "target": self.collections.get("Team BioSyn - Private"),
                "requested_by": "emma.moreau@insillyclo.com",
                "status": Status.PENDING_ADMIN,
                "team": self.teams.get("Équipe Biologie Synthétique"),
                "cheffe_reviewed_by": "jean.martin@insillyclo.com",
                "cheffe_review_comment": "OK pour publication.",
                "cheffe_reviewed_at": timezone.now() - timedelta(days=2),
            },

            # =========================================================
            # REFUSÉ PAR CHEFFE (motif obligatoire)
            # =========================================================
            {
                "target": self.correspondences.get("Project Aliases (Short Names)"),
                "requested_by": "lucas.petit@insillyclo.com",
                "status": Status.REJECTED_BY_CHEFFE,
                "team": self.teams.get("Équipe Synthèse Génomique"),
                "cheffe_reviewed_by": "marie.dupont@insillyclo.com",
                "cheffe_review_comment": "Noms trop spécifiques au projet, non généralisables.",
                "cheffe_reviewed_at": timezone.now() - timedelta(days=5),
            },

            # =========================================================
            # REFUSÉ PAR ADMIN (motif obligatoire)
            # =========================================================
            {
                "target": self.correspondences.get("Freezer Location Mapping"),
                "requested_by": "thomas.leroy@insillyclo.com",
                "status": Status.REJECTED_BY_ADMIN,
                "team": None,
                "admin_reviewed_by": "admin@insillyclo.com",
                "admin_review_comment": "Données internes de localisation, non publiables.",
                "admin_reviewed_at": timezone.now() - timedelta(days=3),
            },

            # =========================================================
            # APPROUVÉ (cheffe + admin)
            # =========================================================
            {
                "target": self.correspondences.get("YTK to Addgene IDs"),
                "requested_by": "claire.bernard@insillyclo.com",
                "status": Status.APPROVED,
                "team": None,
                "cheffe_reviewed_by": "marie.dupont@insillyclo.com",
                "cheffe_review_comment": "Correspondance claire et utile.",
                "cheffe_reviewed_at": timezone.now() - timedelta(days=6),
                "admin_reviewed_by": "admin@insillyclo.com",
                "admin_review_comment": "Validé pour diffusion publique.",
                "admin_reviewed_at": timezone.now() - timedelta(days=5),
            },
        ]

        created = 0
        skipped = 0

        for data in demo_requests:
            target = data.get("target")
            if target is None:
                skipped += 1
                continue

            ct = ContentType.objects.get_for_model(target)

            # Unique constraint guard: no more than one pending request per target
            if data["status"] in (Status.PENDING_CHEFFE, Status.PENDING_ADMIN):
                exists = self.Publication.objects.filter(
                    target_content_type=ct,
                    target_object_id=target.id,
                    status__in=[Status.PENDING_CHEFFE, Status.PENDING_ADMIN],
                ).exists()
                if exists:
                    skipped += 1
                    continue

            kwargs = {
                "requested_by": self.users[data["requested_by"]],
                "target_content_type": ct,
                "target_object_id": target.id,
                "status": data["status"],
            }

            # Team is optional AND model-dependent
            if has_team_field and data.get("team") is not None:
                kwargs["team"] = data["team"]

            # Cheffe review fields
            if data.get("cheffe_reviewed_by"):
                kwargs["cheffe_reviewed_by"] = self.users[data["cheffe_reviewed_by"]]
            if "cheffe_review_comment" in data:
                kwargs["cheffe_review_comment"] = data.get("cheffe_review_comment", "")
            if data.get("cheffe_reviewed_at"):
                kwargs["cheffe_reviewed_at"] = data["cheffe_reviewed_at"]

            # Admin review fields
            if data.get("admin_reviewed_by"):
                kwargs["admin_reviewed_by"] = self.users[data["admin_reviewed_by"]]
            if "admin_review_comment" in data:
                kwargs["admin_review_comment"] = data.get("admin_review_comment", "")
            if data.get("admin_reviewed_at"):
                kwargs["admin_reviewed_at"] = data["admin_reviewed_at"]

            try:
                self.Publication.objects.create(**kwargs)
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created publication request for {target}"))
            except Exception as e:
                skipped += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to create publication request for {target}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n>>> Publication requests: {created} created, {skipped} skipped"))

    # =====================================================================
    # SUMMARY
    # =====================================================================
    def print_summary(self):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\n✓ Users created: {len(self.users)}")
        self.stdout.write(f"✓ Teams created: {len(self.teams)}")
        self.stdout.write(f"✓ Campaign templates created: {len(self.templates)}")
        self.stdout.write(f"✓ Plasmid collections created: {len(self.collections)}")
        self.stdout.write(f"✓ Plasmids created: {len(self.plasmids)}")
        self.stdout.write(f"✓ Correspondence tables created: {len(self.correspondences)}")
        self.stdout.write(f"✓ Campaigns created: {len(self.campaigns)}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("LOGIN CREDENTIALS (DEMO ACCOUNTS)"))
        self.stdout.write("=" * 80)

        # ------------------------------------------------------------------
        # Superuser
        # ------------------------------------------------------------------
        self.stdout.write("\nSUPERUSER (admin validation):")
        self.stdout.write("  Email: admin@insillyclo.com")
        self.stdout.write("  Password: admin123")

        # ------------------------------------------------------------------
        # Example team owners (mixed staff / non-staff)
        # ------------------------------------------------------------------
        self.stdout.write("\nTEAM OWNERS (mixed roles):")
        self.stdout.write("  marie.dupont@insillyclo.com | Password: marie123 | staff")
        self.stdout.write("  jean.martin@insillyclo.com  | Password: jean123  | staff")
        self.stdout.write("  claire.bernard@insillyclo.com | Password: claire123 | staff")
        self.stdout.write("  sophie.rousseau@insillyclo.com | Password: sophie123 | non-staff")
        self.stdout.write("  lea.fournier@insillyclo.com | Password: lea123 | non-staff")
        self.stdout.write("  antoine.martin@insillyclo.com | Password: antoine123 | non-staff")

        # ------------------------------------------------------------------
        # Regular users
        # ------------------------------------------------------------------
        self.stdout.write("\nREGULAR USERS (contributors / members):")
        self.stdout.write("  lucas.petit@insillyclo.com | Password: lucas123")
        self.stdout.write("  emma.moreau@insillyclo.com | Password: emma123")
        self.stdout.write("  thomas.leroy@insillyclo.com | Password: thomas123")
        self.stdout.write("  julie.simon@insillyclo.com | Password: julie123")
        self.stdout.write("  clara.dubois@insillyclo.com | Password: clara123")
        self.stdout.write("  nicolas.bernard@insillyclo.com | Password: nicolas123")
        self.stdout.write("  pierre.garcia@insillyclo.com | Password: pierre123")
        self.stdout.write("  camille.roux@insillyclo.com | Password: camille123")

        # ------------------------------------------------------------------
        # Usage hints
        # ------------------------------------------------------------------
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("USAGE NOTES"))
        self.stdout.write("=" * 80)

        self.stdout.write(
            "\n• Some publication requests are:\n"
            "  - pending cheffe (team validation)\n"
            "  - pending admin (no team or cheffe-approved)\n"
            "  - rejected (with mandatory comments)\n"
            "  - approved (cheffe + admin)\n"
        )

        self.stdout.write(
            "• Some correspondence tables and collections:\n"
            "  - belong to teams\n"
            "  - are personal (no team)\n"
            "  - are public or private\n"
        )

        self.stdout.write(
            "• Team owners are not always staff (intentional).\n"
        )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Run: python manage.py runserver"))
        self.stdout.write("=" * 80 + "\n")
