import os
import shutil
import uuid
import zipfile
import pathlib
import traceback
import glob
import re
import pandas as pd

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from Bio import SeqIO

# Imports du projet
import insillyclo.observer
import insillyclo.simulator
import insillyclo.data_source

from .models import Campaign
from apps.plasmids.models import Plasmid, PlasmidCollection, PlasmidAnnotation

from django.views.decorators.http import require_POST

# ==========================================
# 1. CONSTANTES & CONFIGURATION
# ==========================================

COLORS = {
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


# ==========================================
# 2. FONCTIONS UTILITAIRES (VISUALISATION)
# ==========================================

def detect_overlaps_and_adjust(features_list):
    """Détecte les chevauchements visuels et ajuste les niveaux des labels."""
    # Trier par position centrale
    features_sorted = sorted(features_list, key=lambda f: f["visual_center"])
    
    for current_feature in features_sorted:
        current_feature["label_level"] = 0
        
        for test_level in range(3):
            has_overlap = False
            
            for other_feature in features_sorted:
                if other_feature == current_feature: continue
                
                if other_feature.get("label_level", 0) != test_level: continue
                
                # Calcul des positions horizontales (avec marge de 5px)
                c_left = current_feature["visual_center"] - current_feature["label_text_width"] / 2
                c_right = current_feature["visual_center"] + current_feature["label_text_width"] / 2
                o_left = other_feature["visual_center"] - other_feature["label_text_width"] / 2
                o_right = other_feature["visual_center"] + other_feature["label_text_width"] / 2
                
                if not (c_right + 5 < o_left or o_right + 5 < c_left):
                    has_overlap = True
                    break
            
            if not has_overlap:
                current_feature["label_level"] = test_level
                break

def get_plasmid_visual_data(gb_path):
    """
    Lit un fichier .gb et prépare les données pour le rendu SVG/HTML.
    """
    try:
        record = next(SeqIO.parse(gb_path, "genbank"))
    except:
        return None

    # --- Extraction des features ---
    features = []
    for f in record.features:
        if f.type == 'source': continue
        
        # Récupération Label
        label = ""
        if 'label' in f.qualifiers: label = f.qualifiers['label'][0]
        elif 'gene' in f.qualifiers: label = f.qualifiers['gene'][0]
        elif 'note' in f.qualifiers: label = f.qualifiers['note'][0]
        else: label = f.type

        features.append({
            "start": int(f.location.start),
            "end": int(f.location.end),
            "length": int(f.location.end) - int(f.location.start),
            "label": label,
            "type": f.type,
            "strand": f.location.strand if f.location.strand else 1,
            "color": COLORS.get(f.type, "#CCCCCC"),
        })

    # --- Calculs graphiques ---
    VISUAL_WIDTH = 900
    seq_length = len(record.seq)
    ratio = VISUAL_WIDTH / max(seq_length, 1)
    
    # Trier les features par position de départ
    features = sorted(features, key=lambda f: f["start"])
    
    external_label_counter = 0
    for f in features:
        f["visual_width"] = max(2, int(f["length"] * ratio))
        f["visual_left"] = int(f["start"] * ratio)
        f["visual_center"] = f["visual_left"] + f["visual_width"] // 2

        # Calcul des points SVG pour les flèches
        w = f["visual_width"]
        h = 20
        d = 6 # Profondeur pointe

        if f["strand"] == 1: # Forward
            f["svg_points"] = f"0,0 {w-d},0 {w},{h//2} {w-d},{h} 0,{h}"
        elif f["strand"] == -1: # Reverse
            f["svg_points"] = f"{d},0 {w},0 {w},{h} {d},{h} 0,{h//2}"
        else: # Rectangle
            f["svg_points"] = f"0,0 {w},0 {w},{h} 0,{h}"

        # Gestion des Labels
        label_text_width = len(f.get("label", "")) * 8
        f["label_text_width"] = label_text_width

        if label_text_width <= f["visual_width"] - 10:
            f["label_position"] = "inside"
            f["label_side"] = None
            f["label_level"] = 0
        else:
            f["label_position"] = "outside"
            f["label_side"] = "above" if external_label_counter % 2 == 0 else "below"
            f["label_level"] = 0
            external_label_counter += 1

    # --- Chevauchement et niveaux ---
    features_above = [f for f in features if f.get("label_position") == "outside" and f.get("label_side") == "above"]
    features_below = [f for f in features if f.get("label_position") == "outside" and f.get("label_side") == "below"]
    
    detect_overlaps_and_adjust(features_above)
    detect_overlaps_and_adjust(features_below)

    # --- CSS Final ---
    for f in features:
        if f.get("label_position") == "outside":
            level = f.get("label_level", 0)
            if f["label_side"] == "above":
                f["css_top"] = f"{-15 - (level * 15)}px"
                f["css_connector"] = "bottom: -15px;"
            else:
                f["css_top"] = f"{60 + (level * 15)}px"
                f["css_connector"] = "top: -15px;"

    return {
        "filename": gb_path.name,
        "name": record.description or record.id,
        "length": seq_length,
        "features": features,
        "visual_width": VISUAL_WIDTH
    }


# ==========================================
# 3. FONCTIONS UTILITAIRES (FILES)
# ==========================================

def handle_file_upload_or_recover(request, file_key, folder_name, work_dir, old_path_src=None, clear_flag=False):
    dest_dir = work_dir / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Cas 1 : Nouveau fichier uploadé
    if file_key in request.FILES:
        f = request.FILES[file_key]
        dest_path = dest_dir / f.name
        with open(dest_path, 'wb+') as destination:
            for chunk in f.chunks(): destination.write(chunk)
        return dest_path

    # Cas 2 : Demande de suppression
    if clear_flag: return None

    # Cas 3 : Récupération depuis historique
    if old_path_src:
        old_subfolder = old_path_src / folder_name
        
        # S'il y a un dossier dédié (structure standard)
        if old_subfolder.exists():
            files = list(old_subfolder.glob('*'))
            if files:
                shutil.copy(files[0], dest_dir / files[0].name)
                return dest_dir / files[0].name
        
        # Sinon recherche à la racine (rétro-compatibilité)
        else:
            candidates = []
            if folder_name == 'template':
                candidates = list(old_path_src.glob("*template*.*")) + list(old_path_src.glob("*.xlsx"))
            elif folder_name == 'correspondence':
                candidates = [f for f in old_path_src.glob("*.csv") if "conc" not in f.name.lower() and "primer" not in f.name.lower()]
            elif folder_name == 'primers':
                candidates = [f for f in old_path_src.glob("*.csv") if "primer" in f.name.lower()]
            elif folder_name == 'concentrations':
                candidates = [f for f in old_path_src.glob("*.csv") if "conc" in f.name.lower()]

            if candidates:
                shutil.copy(candidates[0], dest_dir / candidates[0].name)
                return dest_dir / candidates[0].name
    return None


# ==========================================
# 4. VUES DJANGO
# ==========================================

def simulation_view(request):
    context = {}
    
    # --- A. RÉCUPÉRATION DES COLLECTIONS ---
    if request.user.is_authenticated:
        context['user_collections'] = PlasmidCollection.objects.filter(
            owner=request.user, is_public=False
        ).annotate(plasmid_count=Count('plasmids'))  
    
    context['public_collections'] = PlasmidCollection.objects.filter(
        is_public=True
    ).annotate(plasmid_count=Count('plasmids'))

    # --- B. PRÉ-REMPLISSAGE (GET from History) ---
    prefill = {}
    if request.method == 'GET' and 'from_sim' in request.GET:
        sim_id = request.GET.get('from_sim')
        try:
            old_campaign = Campaign.objects.get(run_id=sim_id)
            prefill['name'] = (old_campaign.name or "Untitled") + " (Rerun)"
            prefill['old_sim_id'] = sim_id
            
            params = old_campaign.parameters or {}
            prefill['pcr_primers'] = params.get('pcr_primers_text', '')
            prefill['digestion_enzymes'] = params.get('digestion_enzymes', '')
            prefill['default_concentration'] = params.get('default_concentration', 200)
            prefill['use_collections'] = params.get('use_collections', False)
            prefill['selected_collection_ids'] = params.get('collection_ids', [])

            # Détection fichiers existants
            old_abs_path = pathlib.Path(settings.MEDIA_ROOT) / 'simulations' / sim_id
            if old_abs_path.exists():
                if (old_abs_path / 'template').exists() and list((old_abs_path / 'template').glob('*')):
                    prefill['prev_template'] = list((old_abs_path / 'template').glob('*'))[0].name
                elif list(old_abs_path.glob("*template*.*")) or list(old_abs_path.glob("*.xlsx")):
                    prefill['prev_template'] = "Detected from history"

                if (old_abs_path / 'correspondence').exists() and list((old_abs_path / 'correspondence').glob('*')):
                    prefill['prev_correspondence'] = list((old_abs_path / 'correspondence').glob('*'))[0].name
                elif list(old_abs_path.glob("*.csv")):
                    prefill['prev_correspondence'] = "Detected from history"

                zips = [z for z in old_abs_path.glob("*.zip") if "tout_telecharger" not in z.name]
                if zips: prefill['prev_zip'] = zips[0].name

                if (old_abs_path / 'primers').exists() and list((old_abs_path / 'primers').glob('*')):
                    prefill['prev_primers'] = list((old_abs_path / 'primers').glob('*'))[0].name
                elif [f for f in old_abs_path.glob("*.csv") if "primer" in f.name.lower()]: 
                    prefill['prev_primers'] = "Detected from history"

                if (old_abs_path / 'concentrations').exists() and list((old_abs_path / 'concentrations').glob('*')):
                    prefill['prev_concentrations'] = list((old_abs_path / 'concentrations').glob('*'))[0].name
                elif [f for f in old_abs_path.glob("*.csv") if "conc" in f.name.lower()]: 
                    prefill['prev_concentrations'] = "Detected from history"

            context['prefill'] = prefill
            messages.info(request, "Parameters recovered from history.")
        except Campaign.DoesNotExist:
            pass

    # --- C. TRAITEMENT (POST) ---
    if request.method == 'POST':
        try:
            # Création du dossier de simulation
            sim_id = str(uuid.uuid4())[:8]
            sim_rel_path = os.path.join('simulations', sim_id)
            sim_abs_path = pathlib.Path(settings.MEDIA_ROOT) / sim_rel_path
            sim_abs_path.mkdir(parents=True, exist_ok=True)
            work_dir = sim_abs_path

            old_sim_id_post = request.POST.get('old_sim_id')
            old_path_src = (pathlib.Path(settings.MEDIA_ROOT) / 'simulations' / old_sim_id_post) if old_sim_id_post else None

            # --- GESTION DES FICHIERS ---
            path_template = handle_file_upload_or_recover(request, 'template_file', 'template', work_dir, old_path_src)
            if not path_template: raise Exception("Missing Template file.")

            path_mapping = handle_file_upload_or_recover(request, 'correspondence_file', 'correspondence', work_dir, old_path_src)
            if not path_mapping: raise Exception("Missing Correspondence Table.")

            clear_primers = request.POST.get('clear_primers') == 'true'
            clear_concentrations = request.POST.get('clear_concentrations') == 'true'

            path_primers_db = handle_file_upload_or_recover(request, 'primers_file', 'primers', work_dir, old_path_src, clear_flag=clear_primers)
            path_conc = handle_file_upload_or_recover(request, 'concentrations_file', 'concentrations', work_dir, old_path_src, clear_flag=clear_concentrations)

            # --- GESTION DES SÉQUENCES ---
            sequences_dir = work_dir / 'sequences'
            sequences_dir.mkdir(exist_ok=True)
            
            use_collections = request.POST.get('use_collections') == 'on'
            zip_name_display = "sequences.zip"
            selected_ids_str = [] 

            # >>> OPTION A : Utilisation des Collections (BDD)
            if use_collections:
                selected_ids = request.POST.getlist('selected_collections')
                selected_ids_str = selected_ids 
                
                if not selected_ids:
                    raise Exception("Please select at least one collection.")
                
                # Récupération des noms pour le résumé
                selected_cols_objects = PlasmidCollection.objects.filter(id__in=selected_ids)
                names_list = [col.name for col in selected_cols_objects]
                zip_name_display = ", ".join(names_list)

                count_generated = 0
                for col_id in selected_ids:
                    try:
                        col = PlasmidCollection.objects.get(id=col_id)
                        if not col.is_public and col.owner != request.user:
                            continue
                            
                        for plasmid in col.plasmids.all():
                            # Nettoyage ID
                            clean_name = plasmid.identifier
                            if re.search(r'_[0-9a-f]{4}$', clean_name):
                                clean_name = clean_name[:-5]
                            
                            safe_name = "".join([c for c in clean_name if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                            safe_name = safe_name.replace(" ", "_")
                            if not safe_name: safe_name = "plasmid"
                            
                            dest_path = sequences_dir / f"{safe_name}.gb"

                            # Copier le fichier existant
                            file_found = False
                            if plasmid.file_path:
                                src_path = pathlib.Path(plasmid.file_path)
                                if not src_path.is_absolute():
                                    src_path = pathlib.Path(settings.BASE_DIR) / plasmid.file_path
                                
                                if src_path.exists() and src_path.is_file():
                                    try:
                                        shutil.copy(src_path, dest_path)
                                        file_found = True
                                    except Exception:
                                        pass 

                            # Générer un fichier propre si manquant
                            if not file_found:
                                raw_seq = "".join(plasmid.sequence.split()).lower() if plasmid.sequence else ""
                                length = len(raw_seq)
                                short_name = safe_name[:16] # Nom court pour LOCUS
                                
                                header = (
                                    f"LOCUS       {short_name:<16} {length:>10} bp    DNA     linear   UNK 01-JAN-1980\n"
                                    f"DEFINITION  {plasmid.name}\n"
                                    f"ACCESSION   {safe_name}\n"
                                    f"VERSION     {safe_name}.1\n"
                                    f"KEYWORDS    .\n"
                                    f"SOURCE      .\n"
                                    f"  ORGANISM  .\n"
                                )

                                features_block = "FEATURES             Location/Qualifiers\n"
                                
                                db_annotations = plasmid.annotations.all().order_by('start')
                                if db_annotations.exists():
                                    for ann in db_annotations:
                                        s = ann.start + 1
                                        e = ann.end
                                        loc_str = f"{s}..{e}"
                                        if ann.strand == -1: loc_str = f"complement({s}..{e})"
                                        
                                        ftype = ann.feature_type.strip()
                                        if not ftype: ftype = "misc_feature"

                                        features_block += f"     {ftype:<16}{loc_str}\n"
                                        label = ann.label or ftype
                                        features_block += f"                     /label=\"{label}\"\n"
                                        features_block += f"                     /note=\"Imported from Collection\"\n"
                                else:
                                    features_block += f"     misc_feature    1..{length}\n"
                                    features_block += f"                     /label=\"{plasmid.name}\"\n"
                                    features_block += f"                     /note=\"No annotations in DB\"\n"

                                content = f"{header}{features_block}ORIGIN\n        1 {raw_seq}\n//\n"
                                with open(dest_path, "w") as out: out.write(content)
                            
                            count_generated += 1
                    except PlasmidCollection.DoesNotExist:
                        continue
                
                if count_generated == 0:
                    raise Exception("Selected collections are empty or inaccessible.")

            # >>> OPTION B : Utilisation d'un fichier ZIP
            else:
                path_zip = None
                if 'sequences_archive' in request.FILES:
                    zfile = request.FILES['sequences_archive']
                    path_zip = work_dir / zfile.name
                    with open(path_zip, 'wb+') as dest:
                        for chunk in zfile.chunks(): dest.write(chunk)
                    zip_name_display = zfile.name
                elif old_path_src:
                    olds = [z for z in old_path_src.glob("*.zip") if "tout_telecharger" not in z.name]
                    if olds:
                        shutil.copy(olds[0], work_dir / olds[0].name)
                        path_zip = work_dir / olds[0].name
                        zip_name_display = olds[0].name
                
                if path_zip:
                    with zipfile.ZipFile(path_zip, 'r') as z: z.extractall(sequences_dir)
                else:
                    raise Exception("No sequence source provided.")
                
                # --- LOGIQUE D'IMPORT VERS COLLECTION ---
                if request.user.is_authenticated and request.POST.get('save_to_collection') == 'on':
                    try:
                        custom_name = request.POST.get('new_collection_name')
                        if custom_name and custom_name.strip():
                            new_col_name = custom_name.strip()
                        else:
                            sim_name = request.POST.get('simulation_name') or sim_id
                            new_col_name = f"Import: {sim_name} ({sim_id[:6]})"
                        
                        new_collection = PlasmidCollection.objects.create(
                            name=new_col_name, owner=request.user, is_public=False
                        )

                        permanent_storage_dir = pathlib.Path(settings.MEDIA_ROOT) / 'plasmids' / f'user_{request.user.id}'
                        permanent_storage_dir.mkdir(parents=True, exist_ok=True)

                        imported_count = 0
                        for gb_file in sequences_dir.glob("**/*.gb"):
                            try:
                                record = next(SeqIO.parse(gb_file, "genbank"))
                                
                                identifier = record.id
                                if not identifier or identifier == '.' or '<unknown' in identifier:
                                    identifier = gb_file.stem 
                                
                                clean_id = identifier
                                while Plasmid.objects.filter(identifier=clean_id).exists():
                                    clean_id = f"{identifier}_{uuid.uuid4().hex[:4]}"

                                safe_filename = f"{clean_id}_{gb_file.name}"
                                permanent_path = permanent_storage_dir / safe_filename
                                shutil.copy(gb_file, permanent_path)

                                new_plasmid = Plasmid.objects.create(
                                    identifier=clean_id,
                                    name=record.description[:200] if record.description else clean_id,
                                    type="Imported",
                                    sequence=str(record.seq).upper(),
                                    length=len(record.seq),
                                    description=f"Imported from simulation {sim_id}",
                                    collection=new_collection,
                                    file_path=str(permanent_path.relative_to(settings.MEDIA_ROOT)),
                                    is_public=False
                                )

                                for feature in record.features:
                                    if feature.type == 'source': continue
                                    
                                    label = ""
                                    if 'label' in feature.qualifiers: label = feature.qualifiers['label'][0]
                                    elif 'gene' in feature.qualifiers: label = feature.qualifiers['gene'][0]
                                    elif 'note' in feature.qualifiers: label = feature.qualifiers['note'][0]
                                    else: label = feature.type 
                                    
                                    strand_val = feature.location.strand
                                    if strand_val is None: strand_val = 1

                                    PlasmidAnnotation.objects.create(
                                        plasmid=new_plasmid,
                                        feature_type=feature.type,
                                        start=int(feature.location.start), 
                                        end=int(feature.location.end),
                                        strand=strand_val,
                                        label=label[:200],
                                        qualifiers=feature.qualifiers
                                    )
                                imported_count += 1
                            
                            except Exception as e:
                                print(f"Failed to import plasmid {gb_file}: {e}")
                                continue 

                        if imported_count > 0:
                            messages.success(request, f"Collection '{new_col_name}' created with {imported_count} plasmids.")
                        else:
                            new_collection.delete()
                            
                    except Exception as e:
                        traceback.print_exc()
                        messages.warning(request, f"Collection import failed: {str(e)}")

            # --- LANCEMENT DE InSillyClo ---
            pcr_primers = []
            if request.POST.get('pcr_primers'):
                for line in request.POST.get('pcr_primers').splitlines():
                    if ',' in line: pcr_primers.append(tuple(x.strip() for x in line.split(',')[:2]))

            enzymes = [e.strip() for e in request.POST.get('digestion_enzymes', '').split(',') if e.strip()] or None
            def_conc = float(request.POST.get('default_concentration', 200))

            if not path_primers_db: pcr_primers = []

            observer = insillyclo.observer.InSillyCloCliObserver(debug=False, fail_on_error=True)
            output_dir = work_dir / 'results'
            output_dir.mkdir(exist_ok=True)
            gb_files = list(sequences_dir.glob('**/*.gb'))
            
            if not gb_files: 
                raise Exception("No valid .gb files found.")

            try:
                # 1. On lit le fichier de correspondance (CSV)
                df_mapping = pd.read_csv(path_mapping, sep=None, engine='python')
                
                required_ids = df_mapping.iloc[:, 0].dropna().astype(str).str.strip().tolist()
                
                # 2. On fait l'inventaire des fichiers présents
                available_stems = {f.stem.lower() for f in sequences_dir.glob('**/*.gb')}
                
                missing_files = []
                
                for req_id in required_ids:
                    # On ignore les en-têtes potentiels ou lignes vides
                    if req_id.lower() in ['part', 'name', 'id', 'identifier', 'plasmid_id', '']: 
                        continue
                        
                    # La comparaison : est-ce que 'plasmid_A' est dans le dossier ?
                    if req_id.lower() not in available_stems:
                        missing_files.append(req_id)
                
                # 3. Si des fichiers manquent, on lève une erreur précise
                if missing_files:
                    # On affiche les 5 premiers pour ne pas inonder l'écran
                    missing_str = ", ".join(missing_files[:5])
                    if len(missing_files) > 5:
                        missing_str += f" and {len(missing_files) - 5} others..."
                    
                    raise Exception(f"Missing plasmid files! The template asks for these, but they are not in your source: {missing_str}")

            except Exception as e:
                # Si c'est notre erreur "Missing plasmid", on la remonte pour l'afficher à l'utilisateur
                if "Missing plasmid" in str(e):
                    raise e
                # Si pandas n'arrive pas à lire le CSV, on ne bloque pas (on laisse le simulateur essayer)
                print(f"Warning: Could not pre-validate mapping file: {e}")

            insillyclo.simulator.compute_all(
                observer=observer,
                settings=None,
                input_template_filled=path_template,
                input_parts_files=[path_mapping],
                gb_plasmids=gb_files,
                output_dir=output_dir,
                data_source=insillyclo.data_source.DataSourceHardCodedImplementation(),
                primers_file=path_primers_db,
                primer_id_pairs=pcr_primers,
                enzyme_names=enzymes,
                default_mass_concentration=def_conc,
                concentration_file=path_conc,
                sbol_export=False,
            )

            shutil.make_archive(str(work_dir / 'tout_telecharger'), 'zip', output_dir)

            if request.user.is_authenticated:
                relative_input_path = os.path.join('simulations', sim_id, 'template', path_template.name)
                Campaign.objects.create(
                    name=request.POST.get('simulation_name') or "Untitled",
                    owner=request.user,
                    run_id=sim_id,
                    input_file=relative_input_path,
                    parameters={
                        'pcr_primers_text': request.POST.get('pcr_primers', ''),
                        'digestion_enzymes': request.POST.get('digestion_enzymes', ''),
                        'default_concentration': def_conc,
                        'use_collections': use_collections,
                        'collection_ids': [int(i) for i in selected_ids_str], 
                        'template_name': path_template.name,
                        'correspondence_name': path_mapping.name,
                        'archive_name': zip_name_display,
                        'primers_name': path_primers_db.name if path_primers_db else None,
                        'concentrations_name': path_conc.name if path_conc else None
                    },
                    output_files={'files': os.listdir(output_dir)}
                )

            messages.success(request, "Simulation completed successfully!")
            return redirect('simulations:simulation_detail', sim_id=sim_id)

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'simulations/simu.html', context)

    return render(request, 'simulations/simu.html', context)


# ==========================================
# 5. AUTRES VUES (HISTORIQUE, DÉTAILS)
# ==========================================

@login_required
def simulation_history_view(request):
    campaigns = Campaign.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'simulations/history.html', {'campaigns': campaigns})


def simulation_detail_view(request, sim_id):
    campaign = None
    try:
        campaign = Campaign.objects.get(run_id=sim_id)
    except Campaign.DoesNotExist:
        pass

    sim_rel_path = os.path.join('simulations', sim_id)
    sim_abs_path = pathlib.Path(settings.MEDIA_ROOT) / sim_rel_path
    output_dir = sim_abs_path / 'results'

    if not output_dir.exists():
        messages.error(request, "Results not found (expired or deleted).")
        return redirect('simulations:simu')

    # Liste simple des fichiers
    files = sorted([f.name for f in output_dir.iterdir() if f.is_file()])
    
    # --- PRÉPARATION VISUALISATION PLASMIDES ---
    plasmid_visuals = []
    # On cherche tous les .gb dans le dossier résultats
    for gb_file in output_dir.glob("*.gb"):
        visual_data = get_plasmid_visual_data(gb_file)
        if visual_data:
            plasmid_visuals.append(visual_data)
    
    # Trie par nom
    plasmid_visuals.sort(key=lambda x: x['filename'])

    results = {
        'sim_id': sim_id,
        'sim_name': campaign.name if campaign else "Anonymous Simulation",
        'files': files,
        'output_dir_url': f"{settings.MEDIA_URL}simulations/{sim_id}/results",
        'zip_url': f"{settings.MEDIA_URL}simulations/{sim_id}/tout_telecharger.zip" if (sim_abs_path / 'tout_telecharger.zip').exists() else None,
        'plasmid_visuals': plasmid_visuals,
    }
    
    context = {
        'results': results,
        'campaign': campaign
    }
    
    return render(request, 'simulations/simulation_results.html', context)

# ==========================================
# 6. SUPPRESSION
# ==========================================

@login_required
@require_POST
def delete_campaigns_view(request):
    try:
        # On récupère la liste des IDs cochés dans le formulaire HTML
        campaign_ids = request.POST.getlist('campaign_ids')
        
        if not campaign_ids:
            messages.warning(request, "No campaigns selected.")
            return redirect('simulations:history')

        # On récupère les campagnes, mais seulement celles qui appartiennent à l'utilisateur
        campaigns_to_delete = Campaign.objects.filter(id__in=campaign_ids, owner=request.user)
        count = campaigns_to_delete.count()

        if count == 0:
            messages.warning(request, "No valid campaigns found to delete.")
            return redirect('simulations:history')

        # Suppression des fichiers sur le disque
        for campaign in campaigns_to_delete:
            if campaign.run_id:
                sim_path = pathlib.Path(settings.MEDIA_ROOT) / 'simulations' / campaign.run_id
                if sim_path.exists() and sim_path.is_dir():
                    try:
                        shutil.rmtree(sim_path) # Supprime le dossier et tout son contenu
                    except Exception as e:
                        print(f"Error deleting folder {sim_path}: {e}")

        # Suppression en base de données
        campaigns_to_delete.delete()

        messages.success(request, f"Successfully deleted {count} campaign(s).")

    except Exception as e:
        messages.error(request, f"An error occurred during deletion: {e}")

    return redirect('simulations:history')