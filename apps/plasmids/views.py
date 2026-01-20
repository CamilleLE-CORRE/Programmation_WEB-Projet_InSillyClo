from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Plasmid, PlasmidCollection
from .forms import PlasmidSearchForm, PLASMID_TYPE_CHOICES, RESTRICTION_SITE_CHOICES
from .management.genbank import parse_genbank

# class PlasmidList(TemplateView):
#     template_name = "plasmids/plasmid_list.html"

def plasmid_list(request):

    # A connected user can see both public and private plasmid collections
    if request.user.is_authenticated:
        plasmids = Plasmid.objects.all()

    # An unregistered user can only see public plasmid collections
    else:
        plasmids = Plasmid.objects.filter(collection__is_public=True)

    return render(request, 'plasmids/plasmid_list.html', {
        'plasmids': plasmids
    })

def plasmid_detail(request, identifier):
    
    # Get plasmid and verify it exists
    plasmid = get_object_or_404(Plasmid, identifier=identifier)
    
    return render(request, "plasmids/plasmid_detail.html", {
        "plasmid": plasmid
    })

class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PlasmidSearchForm(self.request.GET or None)
        context['form'] = form
        context['PLASMID_TYPE_CHOICES'] = PLASMID_TYPE_CHOICES
        context['RESTRICTION_SITE_CHOICES'] = RESTRICTION_SITE_CHOICES
        plasmids = Plasmid.objects.all()

        if form.is_valid():
            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")
            types = form.cleaned_data.get("types")
            sites = form.cleaned_data.get("sites")

            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)
            if name:
                plasmids = plasmids.filter(name__icontains=name)
            if types:
                plasmids = plasmids.filter(type__in=types)
            if sites:
                for site in sites:
                    plasmids = plasmids.filter(sites__icontains=site)

        context['plasmids'] = plasmids
        return context


class PlasmidSearchResultsView(TemplateView):
    template_name = "plasmids/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PlasmidSearchForm(self.request.GET or None)
        context['form'] = form

        plasmids = Plasmid.objects.all()

        if form.is_valid():
            # Champs texte
            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")
            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)
            if name:
                plasmids = plasmids.filter(name__icontains=name)

            # Types
            for t, _ in PLASMID_TYPE_CHOICES:
                choice = self.request.GET.get(f"type_{t}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(type__icontains=t)
                elif choice == "no":
                    plasmids = plasmids.exclude(type__icontains=t)

            # Sites ER
            for s, _ in RESTRICTION_SITE_CHOICES:
                choice = self.request.GET.get(f"site_{s}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(sites__icontains=s)
                elif choice == "no":
                    plasmids = plasmids.exclude(sites__icontains=s)

        context['plasmids'] = plasmids
        context['PLASMID_TYPE_CHOICES'] = PLASMID_TYPE_CHOICES
        context['RESTRICTION_SITE_CHOICES'] = RESTRICTION_SITE_CHOICES
        return context

colors = {
    "CDS": "#0000FF",
    "rep_origin": "#1C9BFF",
    "promoter": "#66CCFF",
    "misc_feature": "#C2E0FF",
    "protein_bind": "#FF9900",
    "terminator": "#FFCD36",
}


def plasmid_detail(request, identifier):
    plasmid = get_object_or_404(Plasmid, identifier=identifier)

    # Si genbank_data existe et contient des features
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

    VISUAL_WIDTH = 900
    ratio = VISUAL_WIDTH / parsed.get("length", 1)

    for f in parsed.get("features", []):
        f["visual_width"] = max(2, int(f.get("length", 1) * ratio))
        f["visual_left"] = int(f.get("start", 0) * ratio)
        f["visual_center"] = f["visual_left"] + f["visual_width"] // 2

    context = {
        "plasmid": plasmid,
        "parsed": parsed,
        "visual_width": VISUAL_WIDTH,
    }

    return render(request, "plasmids/plasmid_detail.html", context)

