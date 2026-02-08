"""
These codes used to parse correspondence files uploaded by users:
-  Show correspondence list
-  Show correspondence detail
-  Create new correspondence
-  Upload correspondence entries from a file:
    -  Parse file
    -  Validate for conflicts
    -  Write to DB
-  Delete correspondence
"""
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Team
from .forms import CorrespondenceCreateForm, CorrespondenceUploadForm
from .models import Correspondence, CorrespondenceEntry
from apps.correspondences.parsers import parse_correspondence_text
from collections import defaultdict
from .parsers import parse_correspondence_text, parse_correspondence_xlsx



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
        form = CorrespondenceCreateForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            # obj.team = Team.objects.filter(members=request.user).first()
            obj.save()
            messages.success(request, "Correspondence created.")
            return redirect("correspondences:detail", pk=obj.pk)
    else:
        form = CorrespondenceCreateForm(user=request.user)


    return render(request, "correspondences/correspondence_create.html", {"form": form})


@login_required
def correspondence_upload(request, pk: int):
    """
    Upload correspondence entries from a text or .xlsx file.
    - Parses the file
    - Validates for conflicts
    - Writes to DB
    """
    corr = get_object_or_404(Correspondence, pk=pk, owner=request.user)

    if request.method == "POST":
        form = CorrespondenceUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request,
                "correspondences/correspondence_upload.html",
                {"form": form, "correspondence": corr},
            )

        f = form.cleaned_data["file"]
        replace_existing = form.cleaned_data["replace_existing"]

        # ===== Parse file =====
        name = (getattr(f, "name", "") or "").lower()
        if name.endswith(".xlsx"):
            rows, errors = parse_correspondence_xlsx(f)
        else:
            raw = f.read().decode("utf-8", errors="replace")
            rows, errors = parse_correspondence_text(raw)

        # ===== Handle parsing errors FIRST =====
        if errors:
            messages.error(request, "Parsing errors detected. Please fix and re-upload.")
            for e in errors[:10]:
                messages.error(request, e)
            if len(errors) > 10:
                messages.error(request, f"... plus {len(errors) - 10} more errors.")
            return render(
                request,
                "correspondences/correspondence_upload.html",
                {"form": form, "correspondence": corr},
            )

        

        # ===== Conflict detection =====
        # Rule (symmetric):
        # 1) Same (display_name, entry_type) cannot map to multiple identifiers
        # 2) Same (identifier, entry_type) cannot map to multiple display_names
        by_name = defaultdict(set)  # (display_name, entry_type) -> {identifier}
        by_id = defaultdict(set)    # (identifier, entry_type) -> {display_name}

        for identifier, display_name, entry_type in rows:
            et = entry_type or ""
            by_name[(display_name, et)].add(identifier)
            by_id[(identifier, et)].add(display_name)

        conflict_messages = []

        for (display_name, et), identifiers in by_name.items():
            if len(identifiers) > 1:
                conflict_messages.append(
                    f"Conflict: Display name '{display_name}' (type: '{et}') maps to multiple identifiers: "
                    f"{', '.join(sorted(identifiers))}."
                )

        for (identifier, et), display_names in by_id.items():
            if len(display_names) > 1:
                conflict_messages.append(
                    f"Conflict: Identifier '{identifier}' (type: '{et}') maps to multiple display names: "
                    f"{', '.join(sorted(display_names))}."
                )

        if conflict_messages:
            messages.error(request, "Conflicts detected in the uploaded correspondence table.")
            messages.error(request, "Ambiguous mappings are not allowed. Please fix the issues below and re-upload.")
            for msg in conflict_messages[:20]:
                messages.error(request, msg)
            if len(conflict_messages) > 20:
                messages.error(request, f"... plus {len(conflict_messages) - 20} more conflicts.")
            return render(
                request,
                "correspondences/correspondence_upload.html",
                {"form": form, "correspondence": corr},
            )

        # ===== Write to DB =====
        with transaction.atomic():
            if replace_existing:
                corr.entries.all().delete()

            entries = [
                CorrespondenceEntry(
                    correspondence=corr,
                    identifier=identifier,
                    display_name=display_name,
                    entry_type=(entry_type or ""),
                )
                for identifier, display_name, entry_type in rows
            ]
            CorrespondenceEntry.objects.bulk_create(entries)

        messages.success(request, f"Uploaded {len(rows)} entries successfully.")
        return redirect("correspondences:detail", pk=corr.pk)

    # GET
    form = CorrespondenceUploadForm()
    return render(
        request,
        "correspondences/correspondence_upload.html",
        {"form": form, "correspondence": corr},
    )


@login_required
def correspondence_delete(request, pk: int):
    #corr = get_object_or_404(Correspondence, pk=pk, owner=request.user)
    corr = get_object_or_404(Correspondence, pk=pk)

    # Collection owner and cheffe can delete
    is_owner = (corr.owner_id == request.user.id)
    is_team_owner = (corr.team_id is not None and corr.team.owner_id == request.user.id)

    if not (is_owner or is_team_owner):
        raise PermissionDenied("You are not allowed to delete this correspondence.")


    if request.method == "POST":
        name = corr.name
        corr.delete()
        messages.success(request, f"Deleted correspondence '{name}'.")
        return redirect("correspondences:list")

    return render(request, "correspondences/correspondence_confirm_delete.html", {"correspondence": corr})