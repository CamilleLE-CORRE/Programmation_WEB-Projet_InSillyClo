import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CorrespondenceCreateForm, CorrespondenceUploadForm
from .models import Correspondence, CorrespondenceEntry


def parse_correspondence_text(raw_text: str):
    rows = []
    errors = []
    seen_identifiers = set()

    for lineno, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = re.split(r"[,\t;]+|\s{2,}", line)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) not in (2, 3):
            errors.append(f"Line {lineno}: expected 2 or 3 columns, got {len(parts)} -> {line}")
            continue

        identifier = parts[0]
        display_name = parts[1]
        entry_type = parts[2] if len(parts) == 3 else ""

        if identifier in seen_identifiers:
            errors.append(f"Line {lineno}: duplicate identifier '{identifier}' in file.")
            continue
        seen_identifiers.add(identifier)

        rows.append((identifier, display_name, entry_type))

    return rows, errors


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
    corr = get_object_or_404(Correspondence, pk=pk, owner=request.user)

    if request.method == "POST":
        form = CorrespondenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            replace_existing = form.cleaned_data["replace_existing"]

            raw = f.read().decode("utf-8", errors="replace")
            rows, errors = parse_correspondence_text(raw)

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
