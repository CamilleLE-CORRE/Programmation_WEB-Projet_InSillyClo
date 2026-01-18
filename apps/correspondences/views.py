import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CorrespondenceCreateForm, CorrespondenceUploadForm
from .models import Correspondence, CorrespondenceEntry
from apps.correspondences.parsers import parse_correspondence_text
from collections import defaultdict


def correspondence_list(request):
    qs = Correspondence.objects.all()
    if request.user.is_authenticated:
        qs = qs.filter(Q(is_public=True) | Q(owner=request.user))
    else:
        qs = qs.filter(is_public=True)
    qs = qs.annotate(entries_count=Count("entries")).order_by("id", "name")
    return render(request, "correspondences/correspondence_list.html", {"correspondences": qs})


def correspondence_detail(request, pk: int):
    qs = Correspondence.objects.all()
    if request.user.is_authenticated:
        qs = qs.filter(Q(is_public=True) | Q(owner=request.user))
    else:
        qs = qs.filter(is_public=True)

    correspondence = get_object_or_404(qs, pk=pk)
    entries = correspondence.entries.all().order_by("identifier")
    return render(
        request,
        "correspondences/correspondence_detail.html",
        {"correspondence": correspondence, "entries": entries},
    )


@login_required
def correspondence_create(request):
    if request.method == "POST":
        form = CorrespondenceCreateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            messages.success(request, "Correspondence created.")
            return redirect("correspondences:detail", pk=obj.pk)
    else:
        form = CorrespondenceCreateForm()

    return render(request, "correspondences/correspondence_create.html", {"form": form})


@login_required
def correspondence_upload(request, pk: int):
    """
    POST
    ├─ form.is_valid()
    │   ├─ read file
    │   ├─ parse_correspondence_text(raw)
    │   │    ↳ rows, errors
    │   ├─ if errors:  ← CSV/TSV
    │   │      return
    │   ├─ with transaction.atomic():
    │   │     ├─ delete existing (optional)
    │   │     ├─ bulk_create entries  
    │   └─ success
    """
    corr = get_object_or_404(Correspondence, pk=pk, owner=request.user)

    if request.method == "POST":
        form = CorrespondenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            replace_existing = form.cleaned_data["replace_existing"]

            raw = f.read().decode("utf-8", errors="replace")
            rows, errors = parse_correspondence_text(raw)

            # ======= Conflits detection =======
            by_name = defaultdict(set)   # (display_name, entry_type) -> set(identifier)
            by_identifier = defaultdict(set)  # identifier -> set((display_name, entry_type))
            
            for identifier, display_name, entry_type in rows:
                key_name = (display_name, entry_type or "")
                key_id = (identifier, entry_type or "")
                by_name[key_name].add(identifier)
                by_identifier[identifier].add((display_name))
            
            conflict_messages = []

            # (1) Same display_name --> multiple identifiers
            for (display_name, entry_type), identifiers in by_name.items():
                if len(identifiers) > 1:
                    conflict_messages.append(
                        f"Conflict: Display name '{display_name}' (type: '{entry_type}') maps to multiple identifiers: {', '.join(sorted(identifiers))}."
                    )
            # (2) Same identifier --> multiple display_names
            for identifier, name_types in by_identifier.items():
                if len(name_types) > 1:
                    conflict_messages.append(
                        f"Conflict: Identifier '{identifier}' maps to multiple display names: {', '.join(sorted(name_types))}."
                    )
            if conflict_messages:
                # We do not automatically resolve ambiguous correspondences.
                # User must fix the correspondence table.
                messages.error(
                    request,
                    "Conflicts detected in the uploaded correspondence table:\n" 
                    "Ambiguous mapping are not allowed."
                    "Please fix the following issues and re-upload:\n" 
                )
                for msg in conflict_messages:
                    messages.error(request, msg)
                return render(request, "correspondences/correspondence_upload.html", {"form": form, "correspondence": corr})
            # ===================================

            # ============= Handle parsing errors=============
            if errors:
                for e in errors[:10]:
                    messages.error(request, e)
                if len(errors) > 10:
                    messages.error(request, f"... plus {len(errors)-10} more errors.")
                return render(request, "correspondences/correspondence_upload.html", {"form": form, "correspondence": corr})

            with transaction.atomic():
                if replace_existing:
                    corr.entries.all().delete()

                entries = [
                    CorrespondenceEntry(
                        correspondence=corr,
                        identifier=identifier,
                        display_name=display_name,
                        entry_type=entry_type,
                    )
                    for identifier, display_name, entry_type in rows
                ]
                CorrespondenceEntry.objects.bulk_create(entries)

            messages.success(request, f"Uploaded {len(rows)} entries successfully.")
            return redirect("correspondences:detail", pk=corr.pk)
    else:
        form = CorrespondenceUploadForm()

    return render(request, "correspondences/correspondence_upload.html", {"form": form, "correspondence": corr})
