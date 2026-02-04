import io
import zipfile
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from django.db import transaction
from django.utils.text import slugify

from Bio import SeqIO

from .models import Plasmid, PlasmidCollection


@dataclass
class ImportResult:
    created: int
    skipped: int
    errors: List[str]


def _iter_genbank_bytes_from_upload(uploaded_file) -> Iterable[Tuple[str, bytes]]:
    """
    Yield (filename, bytes) for each genbank file found.
    Supports:
      - .gb/.gbk single file
      - .zip containing multiple .gb/.gbk
    """
    name = (uploaded_file.name or "").lower()

    if name.endswith(".zip"):
        # Django UploadedFile is file-like; must read bytes
        data = uploaded_file.read()
        zf = zipfile.ZipFile(io.BytesIO(data))
        for info in zf.infolist():
            if info.is_dir():
                continue
            fn = info.filename.lower()
            if fn.endswith(".gb") or fn.endswith(".gbk"):
                yield (info.filename, zf.read(info.filename))
    else:
        # .gb/.gbk
        yield (uploaded_file.name, uploaded_file.read())


def _parse_genbank_records(file_bytes: bytes, source_name: str):
    """
    Parse one genbank content and yield SeqRecord.
    """
    handle = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
    # genbank format name in biopython is "genbank"
    return SeqIO.parse(handle, "genbank")


def _pick_identifier(record) -> str:
    """
    Decide plasmid identifier.
    - Prefer record.id if usable
    - fallback to record.name
    """
    # Biopython record.id sometimes contains weird things; you can normalize if needed
    ident = (getattr(record, "id", "") or "").strip()
    if ident and ident.lower() != "<unknown id>":
        return ident
    name = (getattr(record, "name", "") or "").strip()
    return name or "unknown"


@transaction.atomic
def import_plasmids_from_upload(
    *,
    uploaded_file,
    owner,
    collection: Optional[PlasmidCollection] = None
) -> ImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []

    for filename, content in _iter_genbank_bytes_from_upload(uploaded_file):
        try:
            records = list(_parse_genbank_records(content, filename))
            if not records:
                errors.append(f"{filename}: 没有解析到 GenBank record")
                continue

            for rec in records:
                identifier = _pick_identifier(rec)
                seq = str(rec.seq) if getattr(rec, "seq", None) is not None else ""

                # If plasmid with same owner+identifier exists, skip
                if Plasmid.objects.filter(owner=owner, identifier=identifier).exists():
                    skipped += 1
                    continue

                plasmid = Plasmid.objects.create(
                    owner=owner,
                    identifier=identifier,
                    sequence=seq,
                    genbank_data=filename,     
                    collection=collection,          
                )
                created += 1

        except Exception as e:
            errors.append(f"{filename}: Upload failed{e}")

    return ImportResult(created=created, skipped=skipped, errors=errors)


def get_or_create_target_collection(*, owner, target_collection, new_collection_name: str):
    """
    Return a collection or None.
    """
    if target_collection:
        return target_collection

    name = (new_collection_name or "").strip()
    if not name:
        return None

    # Create a new collection
    return PlasmidCollection.objects.create(
        owner=owner,
        name=name,
        is_public=False,
    )
