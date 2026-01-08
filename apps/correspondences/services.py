"""
These codes used to convert "display_name" (user seen) into "identifier".
And also to solve the conflict when uploading correspondence with existing identifiers or duplicate identifiers in the file.
"""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .models import Correspondence, CorrespondenceEntry


@dataclass
class ResolveResult:
    ok: bool
    identifier: Optional[str] = None
    reason: Optional[str] = None
    matches: Optional[list[str]] = None

class CorrespondenceResolver:
    """
    Resolve display_name to identifier using a correspondence.
    Resolve a single display_name to identifier.
    Support 2 sources of correspondence table:
        (1) from database correspondence entries
        (2) from uploaded correspondence file (in memory)
    """

    def __init__(
        self,
        correspondence_ids: Optional[Iterable[int]] = None,
        temp_rows: Optional[Sequence[tuple[str, str, str]]] = None,  # (identifier, display_name, entry_type)
    ):
        self.correspondence_ids = list(correspondence_ids) if correspondence_ids else []

        self._temp_map = {}
        if temp_rows:
            for identifier, display_name, entry_type in temp_rows:
                key = (display_name, entry_type or "")
                self._temp_map.setdefault(key, set()).add(identifier)


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