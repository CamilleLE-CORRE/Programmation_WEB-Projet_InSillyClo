import os
import shutil
import uuid
import zipfile
import pathlib
import traceback
import glob

from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count

# Imports du projet (InSillyClo)
import insillyclo.observer
import insillyclo.simulator
import insillyclo.data_source

# Import de TES modèles
from .models import Campaign
# Import des modèles du groupe (Plasmids)
from apps.plasmids.models import PlasmidCollection

# --- 1. VUE PRINCIPALE (FORMULAIRE & TRAITEMENT) ---
def simulation_view(request):
    context = {}
    
    # A. Chargement des collections
    if request.user.is_authenticated:
        context['user_collections'] = PlasmidCollection.objects.filter(
            owner=request.user, is_public=False
        ).annotate(plasmid_count=Count('plasmids'))  
    context['public_collections'] = PlasmidCollection.objects.filter(
        is_public=True
    ).annotate(plasmid_count=Count('plasmids'))

    # B. PRÉ-REMPLISSAGE (GET)
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

            if prefill['use_collections']:
                prefill['selected_collection_ids'] = list(old_campaign.collections_used.values_list('id', flat=True))

            # Fichiers existants
            old_abs_path = os.path.join(settings.MEDIA_ROOT, 'simulations', sim_id)
            if os.path.exists(old_abs_path):
                tpls = glob.glob(os.path.join(old_abs_path, "*template*.*")) + glob.glob(os.path.join(old_abs_path, "*.xlsx"))
                if tpls: prefill['prev_template'] = os.path.basename(tpls[0])
                
                csvs = [f for f in glob.glob(os.path.join(old_abs_path, "*.csv")) if "concs" not in f and "primers" not in f]
                if csvs: prefill['prev_correspondence'] = os.path.basename(csvs[0])
                
                zips = [z for z in glob.glob(os.path.join(old_abs_path, "*.zip")) if "tout_telecharger" not in z]
                if zips: prefill['prev_zip'] = os.path.basename(zips[0])

            context['prefill'] = prefill
            messages.info(request, "Parameters recovered from history.")
        except Campaign.DoesNotExist:
            pass

    # C. TRAITEMENT (POST)
    if request.method == 'POST':
        try:
            sim_id = str(uuid.uuid4())[:8]
            sim_rel_path = os.path.join('simulations', sim_id)
            sim_abs_path = os.path.join(settings.MEDIA_ROOT, sim_rel_path)
            
            os.makedirs(sim_abs_path, exist_ok=True)
            fs = FileSystemStorage(location=sim_abs_path)
            work_dir = pathlib.Path(sim_abs_path)

            old_sim_id_post = request.POST.get('old_sim_id')
            old_path_src = pathlib.Path(settings.MEDIA_ROOT) / 'simulations' / old_sim_id_post if old_sim_id_post else None

            # 1. Template
            path_template = None
            if 'template_file' in request.FILES:
                f = request.FILES['template_file']
                path_template = work_dir / fs.save(f.name, f)
            elif old_path_src:
                olds = list(old_path_src.glob("*template*.*")) + list(old_path_src.glob("*.xlsx"))
                if olds:
                    shutil.copy(olds[0], work_dir / olds[0].name)
                    path_template = work_dir / olds[0].name
            if not path_template: raise Exception("Missing Template file.")

            # 2. Correspondance
            path_mapping = None
            if 'correspondence_file' in request.FILES:
                f = request.FILES['correspondence_file']
                path_mapping = work_dir / fs.save(f.name, f)
            elif old_path_src:
                olds = [f for f in old_path_src.glob("*.csv") if "concs" not in f.name and "primers" not in f.name]
                if olds:
                    shutil.copy(olds[0], work_dir / olds[0].name)
                    path_mapping = work_dir / olds[0].name
            if not path_mapping: raise Exception("Missing Correspondence Table.")

            # 3. Séquences
            sequences_dir = work_dir / 'sequences'
            sequences_dir.mkdir(exist_ok=True)
            use_collections = request.POST.get('use_collections') == 'on'

            if use_collections:
                selected_ids = request.POST.getlist('selected_collections')
                if not selected_ids: raise Exception("No collection selected.")
                for pid in selected_ids:
                    try:
                        col = PlasmidCollection.objects.get(id=pid)
                        for plasmid in col.plasmids.all():
                            safe_name = "".join([c for c in plasmid.name if c.isalnum() or c in (' ', '.', '_')]).strip()
                            with open(sequences_dir / f"{safe_name}.gb", "w") as out:
                                out.write(plasmid.sequence_gb)
                    except PlasmidCollection.DoesNotExist:
                        continue
            else:
                if 'sequences_archive' in request.FILES:
                    zfile = request.FILES['sequences_archive']
                    path_zip = work_dir / fs.save(zfile.name, zfile)
                    with zipfile.ZipFile(path_zip, 'r') as z: z.extractall(sequences_dir)
                elif old_path_src:
                    olds = [z for z in old_path_src.glob("*.zip") if "tout_telecharger" not in z.name]
                    if olds:
                        shutil.copy(olds[0], work_dir / olds[0].name)
                        with zipfile.ZipFile(work_dir / olds[0].name, 'r') as z: z.extractall(sequences_dir)
                    else: raise Exception("Missing Zip Archive.")
                else: raise Exception("No sequence source provided.")

            # --- 4. PARAMÈTRES OPTIONNELS (Fichiers) ---
            # C'est ce bloc qui manquait et causait l'erreur !
            
            # A. Fichier d'amorces (Primers DB)
            path_primers_db = None
            if 'primers_file' in request.FILES:
                p_file = request.FILES['primers_file']
                path_primers_db = work_dir / fs.save(p_file.name, p_file)
            
            # B. Fichier de concentrations
            path_conc = None
            if 'concentrations_file' in request.FILES:
                c_file = request.FILES['concentrations_file']
                path_conc = work_dir / fs.save(c_file.name, c_file)

            # --- 5. PARAMÈTRES TEXTE ---
            pcr_primers = []
            if request.POST.get('pcr_primers'):
                for line in request.POST.get('pcr_primers').splitlines():
                    if ',' in line: pcr_primers.append(tuple(x.strip() for x in line.split(',')[:2]))

            enzymes = [e.strip() for e in request.POST.get('digestion_enzymes', '').split(',') if e.strip()] or None
            def_conc = float(request.POST.get('default_concentration', 200))

            # --- 6. LANCEMENT INSILLYCLO ---
            observer = insillyclo.observer.InSillyCloCliObserver(debug=False, fail_on_error=True)
            output_dir = work_dir / 'results'
            output_dir.mkdir(exist_ok=True)
            
            gb_files = list(sequences_dir.glob('**/*.gb'))
            if not gb_files: raise Exception("No .gb files found.")

            insillyclo.simulator.compute_all(
                observer=observer,
                settings=None,
                input_template_filled=path_template,
                input_parts_files=[path_mapping],
                gb_plasmids=gb_files,
                output_dir=output_dir,
                data_source=insillyclo.data_source.DataSourceHardCodedImplementation(),
                # On passe bien les fichiers optionnels ici
                primers_file=path_primers_db,      # <--- C'était ici que ça plantait (None)
                primer_id_pairs=pcr_primers,
                enzyme_names=enzymes,
                default_mass_concentration=def_conc,
                concentration_file=path_conc,      # <--- Ajouté aussi
                sbol_export=False,
            )

            shutil.make_archive(str(work_dir / 'tout_telecharger'), 'zip', output_dir)

            if request.user.is_authenticated:
                relative_input_path = os.path.join('simulations', sim_id, path_template.name)
                new_campaign = Campaign.objects.create(
                    name=request.POST.get('simulation_name') or "Untitled",
                    owner=request.user,
                    run_id=sim_id,
                    input_file=relative_input_path,
                    parameters={
                        'pcr_primers_text': request.POST.get('pcr_primers', ''),
                        'digestion_enzymes': request.POST.get('digestion_enzymes', ''),
                        'default_concentration': def_conc,
                        'use_collections': use_collections
                    },
                    output_files={'files': os.listdir(output_dir)}
                )
                if use_collections:
                    selected_ids = request.POST.getlist('selected_collections')
                    if selected_ids: new_campaign.collections_used.set(selected_ids)

            messages.success(request, "Simulation completed successfully!")
            return redirect('simulations:simulation_detail', sim_id=sim_id)

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'simulations/simu.html', context)

    return render(request, 'simulations/simu.html', context)

# --- 2. HISTORIQUE ---
@login_required
def simulation_history_view(request):
    # On affiche les campagnes de l'utilisateur, triées par date
    campaigns = Campaign.objects.filter(owner=request.user) # Le tri est déjà fait dans Meta du modèle
    return render(request, 'simulations/history.html', {'campaigns': campaigns})

# --- 3. DÉTAILS / RÉSULTATS ---
def simulation_detail_view(request, sim_id):
    # Récupération de l'objet campagne en base (optionnel mais mieux pour le titre)
    campaign = None
    if request.user.is_authenticated:
        try:
            campaign = Campaign.objects.get(run_id=sim_id)
        except Campaign.DoesNotExist:
            pass

    # Reconstruction du chemin physique
    sim_rel_path = os.path.join('simulations', sim_id)
    sim_abs_path = os.path.join(settings.MEDIA_ROOT, sim_rel_path)
    output_dir = os.path.join(sim_abs_path, 'results')

    if not os.path.exists(output_dir):
        messages.error(request, "Results not found (expired or deleted).")
        return redirect('simulations:simu')

    files = sorted([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))])
    
    results = {
        'sim_id': sim_id,
        'sim_name': campaign.name if campaign else "Anonymous Simulation",
        'files': files,
        # URLs pour l'affichage dans le template
        'output_dir_url': f"{settings.MEDIA_URL}simulations/{sim_id}/results",
        'zip_url': f"{settings.MEDIA_URL}simulations/{sim_id}/tout_telecharger.zip" if os.path.exists(os.path.join(sim_abs_path, 'tout_telecharger.zip')) else None
    }
    return render(request, 'simulations/simulation_results.html', {'results': results})