from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Plasmid
from .forms import (
    PlasmidSearchForm,
    PLASMID_TYPE_CHOICES,
    RESTRICTION_SITE_CHOICES
)

def plasmid_list(request):
    if request.user.is_authenticated:
        plasmids = Plasmid.objects.all()
    else:
        plasmids = Plasmid.objects.filter(collection__is_public=True)

    return render(request, 'plasmids/plasmid_list.html', {
        'plasmids': plasmids
    })


def plasmid_detail(request, identifier):
    plasmid = get_object_or_404(Plasmid, identifier=identifier)
    return render(request, "plasmids/plasmid_detail.html", {
        "plasmid": plasmid
    })


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = PlasmidSearchForm(self.request.GET or None)
        context["form"] = form
        context["PLASMID_TYPE_CHOICES"] = PLASMID_TYPE_CHOICES
        context["RESTRICTION_SITE_CHOICES"] = RESTRICTION_SITE_CHOICES

        # 👉 Aucune recherche au premier chargement
        plasmids = None

        if self.request.GET and form.is_valid():
            plasmids = Plasmid.objects.all()

            # Champs texte
            sequence_pattern = form.cleaned_data.get("sequence_pattern")
            name = form.cleaned_data.get("name")

            if sequence_pattern:
                plasmids = plasmids.filter(sequence__icontains=sequence_pattern)

            if name:
                plasmids = plasmids.filter(name__icontains=name)

            # Types (tri-state)
            for t, _ in PLASMID_TYPE_CHOICES:
                choice = self.request.GET.get(f"type_{t}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(type__icontains=t)
                elif choice == "no":
                    plasmids = plasmids.exclude(type__icontains=t)

            # Sites de restriction (tri-state)
            for s, _ in RESTRICTION_SITE_CHOICES:
                choice = self.request.GET.get(f"site_{s}", "indifferent")
                if choice == "yes":
                    plasmids = plasmids.filter(sites__icontains=s)
                elif choice == "no":
                    plasmids = plasmids.exclude(sites__icontains=s)

        context["plasmids"] = plasmids
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

    # TRI DES FEATURES PAR POSITION DE DÉPART
    parsed["features"] = sorted(parsed.get("features", []), key=lambda f: f.get("start", 0))

    VISUAL_WIDTH = 900
    ratio = VISUAL_WIDTH / parsed.get("length", 1)

    # Compteur pour l'alternance dessus/dessous
    external_label_counter = 0
    
    for f in parsed.get("features", []):
        f["visual_width"] = max(2, int(f.get("length", 1) * ratio))
        f["visual_left"] = int(f.get("start", 0) * ratio)
        f["visual_center"] = f["visual_left"] + f["visual_width"] // 2
        f['visual_width_half'] = f['visual_left'] + (f['visual_width'] / 2)
        f['visual_center'] = f['visual_left'] + f['visual_width'] / 2
        
        # Estimation de la largeur du texte (environ 8 pixels par caractère en bold 14px)
        label_text_width = len(f.get("label", "")) * 8
        
        # Décider si le label peut tenir dans la boîte
        if label_text_width <= f["visual_width"] - 10:  # -10 pour le padding
            f["label_position"] = "inside"
            f["external_label_index"] = None
            f["label_side"] = None
            f["label_level"] = 0
            f["label_text_width"] = 0
        else:
            f["label_position"] = "outside"
            f["external_label_index"] = external_label_counter
            f["label_text_width"] = label_text_width
            
            # Alterner dessus/dessous
            if external_label_counter % 2 == 0:
                f["label_side"] = "above"
            else:
                f["label_side"] = "below"
            
            # Par défaut, niveau 0 (tout au même niveau)
            f["label_level"] = 0
            
            external_label_counter += 1

    # DÉTECTION DES CHEVAUCHEMENTS ET AJUSTEMENT DES NIVEAUX
    features_above = [f for f in parsed["features"] if f.get("label_position") == "outside" and f.get("label_side") == "above"]
    features_below = [f for f in parsed["features"] if f.get("label_position") == "outside" and f.get("label_side") == "below"]
    
    def detect_overlaps_and_adjust(features_list):
        """Détecte les chevauchements et ajuste les niveaux (jusqu'à 3 niveaux)"""
        # Trier par position pour un traitement séquentiel
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
                    
                    # Vérifier le chevauchement (avec une petite marge de 5px)
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
    }

    return render(request, "plasmids/plasmid_detail.html", context)