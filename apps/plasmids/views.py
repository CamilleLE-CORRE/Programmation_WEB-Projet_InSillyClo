from django.views.generic import TemplateView
import json
from django.contrib import messages
from django import forms
from django.forms import ValidationError
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views import View
import re
import zipfile
from pathlib import Path
from io import BytesIO
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required

from apps.correspondences import forms
from apps.accounts.models import Team

from .forms import PlasmidSearchForm,AddPlasmidsToCollectionForm, ImportPlasmidsForm
from .models import PlasmidCollection, Plasmid
from .service import import_plasmids_from_upload, get_or_create_target_collection








def plasmid_list(request):
    if request.user.is_authenticated:
        plasmids = Plasmid.objects.all()
    else:
        plasmids = Plasmid.objects.filter(collection__is_public=True)

    return render(request, 'plasmids/plasmid_list.html', {
        'plasmids': plasmids
    })


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = PlasmidSearchForm(self.request.GET or None)
        context["form"] = form

        context["annotation_constraints"] = [
            {"name": n, "mode": m}
            for n, m in zip(
                self.request.GET.getlist("annotation_name"),
                self.request.GET.getlist("annotation_mode"),
            )
        ]

        context["restriction_constraints"] = [
            {"name": n, "mode": m}
            for n, m in zip(
                self.request.GET.getlist("restriction_name"),
                self.request.GET.getlist("restriction_mode"),
            )
        ]

        plasmids = None

        if self.request.GET and form.is_valid():
            plasmids = Plasmid.objects.all()

            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")

            similar_sequence = self.request.GET.get("similar_sequence", "").strip()
            similarity_threshold = self.request.GET.get("similarity_threshold")

            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)

            if name:
                plasmids = plasmids.filter(name__icontains=name)

            # --- Similarité de séquence ---
            if similar_sequence and len(similar_sequence) >= 3:
                try:
                    similarity_threshold = float(similarity_threshold or 0)
                except ValueError:
                    similarity_threshold = 0

                filtered = []
                for plasmid in plasmids:
                    if has_similar_sequence(
                        plasmid.sequence,
                        similar_sequence,
                        similarity_threshold
                    ):
                        filtered.append(plasmid)

                plasmids = filtered

            # --- Annotations ---
            for c in context["annotation_constraints"]:
                ann_name = c["name"].strip()
                mode = c["mode"]

                if not ann_name:
                    continue

                if mode == "present":
                    plasmids = plasmids.filter(
                        annotations__label__icontains=ann_name
                    )
                elif mode == "absent":
                    plasmids = plasmids.exclude(
                        annotations__label__icontains=ann_name
                    )

            # --- Sites de restriction ---
            for c in context["restriction_constraints"]:
                site = c["name"].strip()
                mode = c["mode"]

                if not site:
                    continue

                if mode == "present":
                    plasmids = plasmids.filter(sites__icontains=site)
                elif mode == "absent":
                    plasmids = plasmids.exclude(sites__icontains=site)

            if hasattr(plasmids, "distinct"):
                plasmids = plasmids.distinct()

        context["plasmids"] = plasmids
        return context



colors = {
    "tRNA": "#070087",
    "CDS": "#0000FF",
    "rep_origin": "#1C9BFF",
    "promoter": "#66CCFF",
    "misc_feature": "#C2E0FF",
    "misc_RNA": "#C2E0FF",
    "protein_bind": "#FF9900",
    "RBS": "#F8B409",
    "terminator": "#FFCD36",
}


def generate_external_link(feature):
    import urllib.parse

    label = feature.get("label", "").strip()
    feature_type = feature.get("type", "").strip().lower()

    if not label:
        return None

    # NCBI nuccore
    base_url = "https://www.ncbi.nlm.nih.gov/nuccore/?term="

    # Gene name
    gene_query = f"({label.split()[0]}[Gene Name])"

    if feature_type in ("cds", "gene"):
        query = gene_query

    elif feature_type == "promoter" or feature_type == "promotor":
        query = f"{gene_query} AND {feature_type}[Feature key]"

    else:
        query = label

    encoded_query = urllib.parse.quote_plus(query)

    return base_url + encoded_query


# Example for CDS :
# https://www.ncbi.nlm.nih.gov/nuccore?term=(camR%5BGene%20Name%5D)

# Example for promoter :
# https://www.ncbi.nlm.nih.gov/nuccore?term=(camR%5BGene%20Name%5D)%20AND%20promoter%5BFeature%20key%5D

# Example for terminator :
# https://www.ncbi.nlm.nih.gov/nuccore/?term=(camR%5BGene+Name%5D)+AND+terminator%5BFeature+key%5D


def has_similar_sequence(sequence, pattern, min_similarity):
    """
    Vérifie si la sequence contient un motif similaire au pattern
    avec une similarité >= min_similarity
    """
    pattern = pattern.upper()
    sequence = sequence.upper()
    pat_len = len(pattern)

    for i in range(len(sequence) - pat_len + 1):
        window = sequence[i:i + pat_len]
        matches = sum(1 for a, b in zip(window, pattern) if a == b)
        similarity = (matches / pat_len) * 100

        if similarity >= min_similarity:
            return True

    return False


def plasmid_detail(request, id):
    plasmid = get_object_or_404(Plasmid, id=id)

    # Récupérer la séquence
    sequence = plasmid.sequence

    # Diviser la séquence en lignes de 50 caractères (pour l'affichage)
    sequence_lines = [plasmid.sequence[i:i+100] for i in range(0, len(plasmid.sequence), 100)]
    formatted_sequence = "\n".join(sequence_lines)

    # Parse features depuis genbank ou annotations
    if plasmid.genbank_data and plasmid.genbank_data.get("features"):
        parsed = parse_genbank(plasmid.genbank_data)
    else:
        # Générer parsed depuis les annotations
        features = []
        for ann in plasmid.annotations.all():
            features.append({
                "start": ann.start + 1,
                "end": ann.end,
                "length": ann.end - ann.start,
                "label": ann.label or ann.feature_type,
                "type": ann.feature_type,
                "strand": ann.strand,
                "color": colors.get(ann.feature_type, "#CCCCCC"),
                "linked_plasmid": None
            })
        parsed = {
            "length": plasmid.length or (max((f["end"] for f in features), default=1)),
            "features": features
        }

    # Trier les features
    parsed["features"] = sorted(parsed.get("features", []), key=lambda f: f.get("start", 0))

    # Calcul de la visualisation
    VISUAL_WIDTH = 900
    ratio = VISUAL_WIDTH / parsed.get("length", 1)
    external_label_counter = 0

    for f in parsed.get("features", []):
        f["visual_width"] = max(2, int(f.get("length", 1) * ratio))
        f["visual_left"] = int(f.get("start", 0) * ratio)
        f["visual_center"] = f["visual_left"] + f["visual_width"] // 2

        # Largeur du texte
        label_text_width = len(f.get("label", "")) * 8
        if label_text_width <= f["visual_width"] - 10:
            f["label_position"] = "inside"
            f["label_side"] = None
            f["label_level"] = 0
        else:
            f["label_position"] = "outside"
            f["label_side"] = "above" if external_label_counter % 2 == 0 else "below"
            f["label_level"] = 0
            f["label_text_width"] = label_text_width
            external_label_counter += 1

        # -----------------------------
        # Génération automatique du lien externe
        # -----------------------------
        f["external_link"] = generate_external_link(f)

    # Chevauchement et niveaux
    features_above = [f for f in parsed["features"] if f.get("label_position") == "outside" and f.get("label_side") == "above"]
    features_below = [f for f in parsed["features"] if f.get("label_position") == "outside" and f.get("label_side") == "below"]
    
    def detect_overlaps_and_adjust(features_list):
        """Détecte les chevauchements et ajuste les niveaux (jusqu'à 3 niveaux)"""
        # Trier par position
        features_sorted = sorted(features_list, key=lambda f: f["visual_center"])
        
        for current_feature in features_sorted:
            # Trouver le niveau approprié en testant les chevauchements à chaque niveau
            current_feature["label_level"] = 0
            
            for test_level in range(3):  # Tester les niveaux 0, 1, 2
                has_overlap = False
                
                # Vérifier si ce niveau est libre (pas de chevauchement avec d'autres features au même niveau)
                for other_feature in features_sorted:
                    if other_feature == current_feature:
                        continue
                    
                    if other_feature["label_level"] != test_level:
                        continue
                    
                    # Calculer les positions horizontales des labels
                    current_left = current_feature["visual_center"] - current_feature["label_text_width"] / 2
                    current_right = current_feature["visual_center"] + current_feature["label_text_width"] / 2
                    other_left = other_feature["visual_center"] - other_feature["label_text_width"] / 2
                    other_right = other_feature["visual_center"] + other_feature["label_text_width"] / 2
                    
                    # Vérifier le chevauchement (avec une marge de 5px)
                    if not (current_right + 5 < other_left or other_right + 5 < current_left):
                        has_overlap = True
                        break
                
                # Si pas de chevauchement à ce niveau, on l'assigne
                if not has_overlap:
                    current_feature["label_level"] = test_level
                    break
    
    detect_overlaps_and_adjust(features_above)
    detect_overlaps_and_adjust(features_below)

    context = {
        "plasmid": plasmid,
        "parsed": parsed,
        "visual_width": VISUAL_WIDTH,
        "sequence": formatted_sequence,
    }

    return render(request, "plasmids/plasmid_detail.html", context)
    


# =================================================================================
# Plasmid Collections Views

class VisibleCollectionQuerysetMixin:
    """Collections visible to current user (public + owned)."""
    def get_queryset(self):
        qs = PlasmidCollection.objects.all()
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(is_public=True) | Q(owner=user)).distinct()
        return qs.filter(is_public=True)

# List Views  
class CollectionListView(VisibleCollectionQuerysetMixin, ListView):
    model = PlasmidCollection
    template_name = "collections/collection_list.html"
    context_object_name = "collections"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["show_create"] = user.is_authenticated
        return ctx


class MyCollectionListView(LoginRequiredMixin, ListView):
    model = PlasmidCollection
    template_name = "collections/collection_list_mine.html"
    context_object_name = "collections"

    def get_queryset(self):
        return PlasmidCollection.objects.filter(owner=self.request.user).order_by("id")

    
# Detail View
class CollectionDetailView(VisibleCollectionQuerysetMixin, DetailView):
    model = PlasmidCollection
    template_name = "collections/collection_detail.html"
    context_object_name = "collection"

# Edit/Create/Delete Views
class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return self.request.user.is_authenticated and obj.owner_id == self.request.user.id


class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = PlasmidCollection
    template_name = "collections/collection_form.html"
    fields = ["name", "team"]
    exclude=["is_public"]

    # Team assignment during creation
    def form_valid(self, form):
        form.instance.owner = self.request.user
        team = Team.objects.filter(members=self.request.user).first()
        form.instance.team = team

        return super().form_valid(form)  


class CollectionUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = PlasmidCollection
    template_name = "collections/collection_form.html"
    fields = ["name", "is_public", "team"]


class CollectionDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = PlasmidCollection
    template_name = "collections/collection_confirm_delete.html"
    context_object_name = "collection"
    success_url = reverse_lazy("plasmids:collection_list")


class CollectionAddPlasmidsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    GET: show collection detail + add form
    POST: move selected plasmids into this collection
    """
    model = PlasmidCollection
    template_name = "collections/collection_detail.html"
    context_object_name = "collection"

    def test_func(self):
        collection = self.get_object()
        return collection.owner_id == self.request.user.id

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        collection = self.object
        # Plasmides already in this collection
        ctx["plasmids"] = collection.plasmids.all().order_by("identifier")

        # Plasmides not in this collection (to add)
        selectable = Plasmid.objects.exclude(collection=collection).order_by("identifier")

        ctx["add_form"] = AddPlasmidsToCollectionForm(queryset=selectable)
        ctx["can_edit"] = True
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        collection = self.object

        selectable = Plasmid.objects.exclude(collection=collection).order_by("identifier")
        form = AddPlasmidsToCollectionForm(request.POST, queryset=selectable)

        if form.is_valid():
            selected = form.cleaned_data["plasmids"]
            count = selected.update(collection=collection)  # Bulk update
            messages.success(request, f"{count} plasmid(s) added to this collection.")
            return redirect(reverse("plasmids:collection_detail", args=[collection.pk]))

    
        ctx = self.get_context_data()
        ctx["add_form"] = form
        return self.render_to_response(ctx)
    



class PlasmidImportView(LoginRequiredMixin, View):
    template_name = "collections/plasmid_import.html"

    def get(self, request):
        form = ImportPlasmidsForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ImportPlasmidsForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded_file = form.cleaned_data["file"]
        target_collection = form.cleaned_data["target_collection"]
        new_collection_name = form.cleaned_data["new_collection_name"]

        collection = get_or_create_target_collection(
            owner=request.user,
            target_collection=target_collection,
            new_collection_name=new_collection_name
        )

        result = import_plasmids_from_upload(
            uploaded_file=uploaded_file,
            owner=request.user,
            collection=collection
        )

        # messages
        messages.success(
            request,
            f"Upload complete: {result.created} created, {result.skipped} skipped."
        )
        if result.errors:
            preview = ";".join(result.errors[:3])
            messages.warning(request, f"Some errors occurred during import: {preview}")

        # redirect
        if collection:
            return redirect(reverse("plasmids:collection_detail", args=[collection.pk]))
        return redirect(reverse("plasmids:plasmid_list"))
    


#========================================================
# Export collection files
def safe_filename(name: str, default="plasmid") -> str:
    name = (name or "").strip() or default
    name = re.sub(r"[^\w\-.]+", "_", name)
    return name[:120]


@login_required
def collection_export_gb_zip(request, pk: int):
    collection = get_object_or_404(PlasmidCollection, pk=pk)

    # Public collections can be exported directly
    if not collection.is_public and collection.owner_id != request.user.id:
        raise Http404("No permission")

    plasmids = collection.plasmids.all()
    if not plasmids.exists():
        raise Http404("Empty collection")

    buffer = BytesIO()
    missing = 0
    added = 0

    # Contents of .zip file about to be exported
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "README.txt",
            f"Exported collection: {collection.name}\n"
            f"Format: GenBank (.gb)\n"
            f"Note: files are read from plasmid.file_path on disk.\n"
        )

        for p in plasmids:
            fp = getattr(p, "file_path", None)
            if not fp:
                missing += 1
                continue

            path = Path(fp)
            if not path.exists() or not path.is_file():
                missing += 1
                continue

            base = safe_filename(p.identifier or p.name or path.stem)
            arcname = f"{base}.gb"

            with open(path, "rb") as f:
                zf.writestr(arcname, f.read())
                added += 1

    if added == 0:
        raise Http404("No GenBank files available to export (missing file_path or files not found on disk).")

    buffer.seek(0)
    zip_name = safe_filename(collection.name, default=f"collection_{collection.id}")
    resp = HttpResponse(buffer.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{zip_name}_genbank.zip"'
    return resp