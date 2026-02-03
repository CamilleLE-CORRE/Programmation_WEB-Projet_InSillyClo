from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Plasmid, PlasmidCollection
from .forms import PlasmidSearchForm, PLASMID_TYPE_CHOICES, RESTRICTION_SITE_CHOICES

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
