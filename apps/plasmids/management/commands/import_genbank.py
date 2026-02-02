from __future__ import annotations

import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    from Bio import SeqIO
except Exception as e:
    SeqIO = None
    BIOPYTHON_IMPORT_ERROR = e
else:
    BIOPYTHON_IMPORT_ERROR = None


def _find_genbank_files(root: Path) -> list[Path]:
    exts = {".gb", ".gbk", ".genbank"}
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            out.append(p)
    return sorted(out)


def _model_has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _safe_set(obj, field: str, value):
    if value is None:
        return
    if _model_has_field(obj.__class__, field):
        setattr(obj, field, value)


class Command(BaseCommand):
    help = "Import GenBank files (.gb/.gbk) from a folder into plasmids database"

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Folder containing GenBank files (recursive)")
        parser.add_argument(
            "--collection",
            dest="collection",
            default=None,
            help="Collection name (defaults to folder name)",
        )
        parser.add_argument(
            "--public",
            dest="public",
            action="store_true",
            help="Mark collection/plasmids public if fields exist",
        )
        parser.add_argument(
            "--update",
            dest="update",
            action="store_true",
            help="Update existing plasmids (otherwise skip existing)",
        )

    def handle(self, *args, **options):
        if SeqIO is None:
            raise CommandError(
                f"Biopython is required. Import error: {BIOPYTHON_IMPORT_ERROR}"
            )

        root = Path(options["path"]).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise CommandError(f"Invalid path: {root}")

        # Import models ONLY when Django is ready
        from apps.plasmids.models import Plasmid, PlasmidCollection, PlasmidAnnotation

        collection_name = options["collection"] or root.name
        make_public = bool(options["public"])
        allow_update = bool(options["update"])

        files = _find_genbank_files(root)
        if not files:
            self.stdout.write(self.style.WARNING(f"No GenBank files found under: {root}"))
            return

        collection, _ = PlasmidCollection.objects.get_or_create(name=collection_name)
        _safe_set(collection, "is_public", make_public)
        _safe_set(collection, "public", make_public)
        collection.save()

        self.stdout.write(f'Importing {len(files)} file(s) into collection "{collection_name}"...')

        created = 0
        updated = 0
        skipped = 0
        failed = 0

        for fp in files:
            try:
                res = self._import_one_file(fp, collection, Plasmid, PlasmidAnnotation, allow_update, make_public)
                if res == "created":
                    created += 1
                elif res == "updated":
                    updated += 1
                elif res == "skipped":
                    skipped += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  FAIL {fp.name}: {e}"))

        self.stdout.write(self.style.SUCCESS("GenBank import summary"))
        self.stdout.write(f"  created: {created}")
        self.stdout.write(f"  updated: {updated}")
        self.stdout.write(f"  skipped: {skipped}")
        self.stdout.write(f"  failed:  {failed}")

    @transaction.atomic
    def _import_one_file(self, fp: Path, collection, Plasmid, PlasmidAnnotation, allow_update: bool, make_public: bool):
        identifier = fp.stem

        # Parse GenBank
        record = SeqIO.read(str(fp), "genbank")

        # --- Find existing plasmid
        # Prefer identifier field if it exists; else fallback on name.
        lookup = {}
        if _model_has_field(Plasmid, "identifier"):
            lookup["identifier"] = identifier
        elif _model_has_field(Plasmid, "name"):
            lookup["name"] = (record.name or identifier)
        else:
            raise CommandError("Plasmid model has neither 'identifier' nor 'name' field.")

        existing = Plasmid.objects.filter(**lookup).first()
        if existing and not allow_update:
            self.stdout.write(f"  Skipped {identifier} (already exists)")
            return "skipped"

        # --- Prepare defaults (only if fields exist)
        defaults = {}
        if _model_has_field(Plasmid, "name"):
            defaults["name"] = (record.name or identifier)
        if _model_has_field(Plasmid, "sequence"):
            defaults["sequence"] = str(record.seq)
        if _model_has_field(Plasmid, "length"):
            defaults["length"] = len(record.seq)
        if _model_has_field(Plasmid, "description"):
            defaults["description"] = record.description or ""
        if _model_has_field(Plasmid, "genbank_data"):
            defaults["genbank_data"] = {
                "topology": record.annotations.get("topology", "linear"),
                "molecule_type": record.annotations.get("molecule_type", ""),
                "date": record.annotations.get("date", ""),
            }
        if _model_has_field(Plasmid, "file_path"):
            defaults["file_path"] = str(fp)

        # collection FK if present
        if _model_has_field(Plasmid, "collection"):
            defaults["collection"] = collection
        elif _model_has_field(Plasmid, "plasmid_collection"):
            defaults["plasmid_collection"] = collection

        # public flags if present
        if _model_has_field(Plasmid, "is_public"):
            defaults["is_public"] = make_public
        if _model_has_field(Plasmid, "public"):
            defaults["public"] = make_public

        plasmid, created = Plasmid.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )

        # --- Delete old annotations if updating
        if not created:
            # Most common related_name is "annotations"
            if hasattr(plasmid, "annotations"):
                plasmid.annotations.all().delete()
            else:
                PlasmidAnnotation.objects.filter(plasmid=plasmid).delete()

        # --- Create annotations
        for feature in getattr(record, "features", []):
            raw_label = (
                feature.qualifiers.get("label", [""])[0]
                or feature.qualifiers.get("gene", [""])[0]
                or ""
            ).strip()

            PlasmidAnnotation.objects.create(
                plasmid=plasmid,
                feature_type=feature.type,
                start=int(feature.location.start),
                end=int(feature.location.end),
                strand=feature.location.strand or 1,
                label=raw_label,
                qualifiers=dict(feature.qualifiers),
            )

        action = "Imported" if created else "Updated"
        self.stdout.write(f"  {action} {identifier}")
        return "created" if created else "updated"
