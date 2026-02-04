from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Dict, Set, Tuple, List

from .models import CorrespondenceEntry


@dataclass
class ResolveResult:
    ok: bool
    identifier: Optional[str] = None
    reason: Optional[str] = None
    matches: Optional[list[str]] = None


@dataclass
class ConflictReport:
    # 上传文件内部：identifier -> [(display_name, entry_type), ...] （当同一identifier映射到多个不同pair时）
    upload_identifier_conflicts: Dict[str, List[Tuple[str, str]]]
    # 上传 vs DB：identifier -> {"db": [...], "upload": [...]} （当同一identifier在DB与上传映射不一致时）
    db_identifier_conflicts: Dict[str, Dict[str, List[Tuple[str, str]]]]


class CorrespondenceResolver:
    """
    Resolve display_name to identifier using a correspondence.
    Support 2 sources:
        (1) database entries
        (2) uploaded file (in memory)
    """

    def __init__(
        self,
        correspondence_ids: Optional[Iterable[int]] = None,
        temp_rows: Optional[Sequence[tuple[str, str, str]]] = None,  # (identifier, display_name, entry_type)
    ):
        self.correspondence_ids = list(correspondence_ids) if correspondence_ids else []

        self._temp_map: Dict[Tuple[str, str], Set[str]] = {}

        # 上传文件反向索引： identifier -> set((display_name, entry_type))
        self._temp_reverse: Dict[str, Set[Tuple[str, str]]] = {}

        if temp_rows:
            for identifier, display_name, entry_type in temp_rows:
                identifier = (identifier or "").strip()
                display_name = (display_name or "").strip()
                entry_type = (entry_type or "").strip()

                if not identifier or not display_name:
                    continue 

                key = (display_name, entry_type)
                self._temp_map.setdefault(key, set()).add(identifier)

                self._temp_reverse.setdefault(identifier, set()).add((display_name, entry_type))

        # 新增：DB反向索引，用来对比上传 vs DB
        self._db_reverse: Dict[str, Set[Tuple[str, str]]] = {}
        if self.correspondence_ids:
            qs = CorrespondenceEntry.objects.filter(correspondence_id__in=self.correspondence_ids)
            for display_name, entry_type, identifier in qs.values_list("display_name", "entry_type", "identifier"):
                identifier = (identifier or "").strip()
                display_name = (display_name or "").strip()
                entry_type = (entry_type or "").strip()
                if not identifier or not display_name:
                    continue
                self._db_reverse.setdefault(identifier, set()).add((display_name, entry_type))

        self.conflicts = self.validate_conflicts()

    def validate_conflicts(self) -> ConflictReport:
        upload_identifier_conflicts: Dict[str, List[Tuple[str, str]]] = {}
        db_identifier_conflicts: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}

        # A) 上传文件内部：同一identifier映射到多个不同(display_name, entry_type)
        for identifier, pairs in self._temp_reverse.items():
            if len(pairs) > 1:
                upload_identifier_conflicts[identifier] = sorted(pairs)

        # B) 上传 vs DB：同一identifier在DB里存在，且映射集合不一致
        for identifier, upload_pairs in self._temp_reverse.items():
            db_pairs = self._db_reverse.get(identifier)
            if db_pairs and db_pairs != upload_pairs:
                db_identifier_conflicts[identifier] = {
                    "db": sorted(db_pairs),
                    "upload": sorted(upload_pairs),
                }

        return ConflictReport(
            upload_identifier_conflicts=upload_identifier_conflicts,
            db_identifier_conflicts=db_identifier_conflicts,
        )

    def resolve(self, display_name: str, entry_type: str = "") -> ResolveResult:
        entry_type = entry_type or ""

        # First check uploaded temp rows
        ids = set(self._temp_map.get((display_name, entry_type), set()))

        # Second check database entries
        if self.correspondence_ids:
            qs = CorrespondenceEntry.objects.filter(
                correspondence_id__in=self.correspondence_ids,
                display_name=display_name,
            )
            if entry_type:
                qs = qs.filter(entry_type=entry_type)

            ids |= set(qs.values_list("identifier", flat=True).distinct())

        ids = sorted(ids)

        if len(ids) == 0:
            return ResolveResult(ok=False, reason="not_found")
        if len(ids) > 1:
            return ResolveResult(ok=False, reason="ambiguous", matches=ids)
        return ResolveResult(ok=True, identifier=ids[0])
