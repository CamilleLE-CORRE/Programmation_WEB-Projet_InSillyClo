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

from .models import Campaign
from apps.plasmids.models import PlasmidCollection

# --- FONCTION UTILITAIRE CORRIGÉE (Priorité : Upload > Clear > History) ---
def handle_file_upload_or_recover(request, file_key, folder_name, work_dir, old_path_src=None, clear_flag=False):
    dest_dir = work_dir / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. PRIORITY 1 : Nouvel Upload (L'emporte toujours)
    if file_key in request.FILES:
        f = request.FILES[file_key]
        dest_path = dest_dir / f.name
        with open(dest_path, 'wb+') as destination:
            for chunk in f.chunks(): destination.write(chunk)
        return dest_path

    # 2. PRIORITY 2 : Demande de suppression explicite
    # Si pas d'upload et qu'on a demandé de supprimer ("Remove"), on renvoie None
    if clear_flag:
        return None

    # 3. PRIORITY 3 : Récupération Historique
    if old_path_src:
        # A. Nouveau système (dossiers séparés)
        old_subfolder = old_path_src / folder_name
        if old_subfolder.exists():
            files = list(old_subfolder.glob('*'))
            if files:
                shutil.copy(files[0], dest_dir / files[0].name)
                return dest_dir / files[0].name
        
        # B. Fallback (Ancien système "tout à la racine")
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


# --- VUE PRINCIPALE ---
def simulation_view(request):
    context = {}
    
    if request.user.is_authenticated:
        context['user_collections'] = PlasmidCollection.objects.filter(
            owner=request.user, is_public=False
        ).annotate(plasmid_count=Count('plasmids'))  
    context['public_collections'] = PlasmidCollection.objects.filter(
        is_public=True
    ).annotate(plasmid_count=Count('plasmids'))

    # --- B. PRÉ-REMPLISSAGE (GET) ---
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

            # DÉTECTION DES FICHIERS POUR L'INTERFACE (UI)
            old_abs_path = pathlib.Path(settings.MEDIA_ROOT) / 'simulations' / sim_id
            if old_abs_path.exists():
                
                # 1. Template
                if (old_abs_path / 'template').exists() and list((old_abs_path / 'template').glob('*')):
                    prefill['prev_template'] = list((old_abs_path / 'template').glob('*'))[0].name
                elif list(old_abs_path.glob("*template*.*")) or list(old_abs_path.glob("*.xlsx")):
                    prefill['prev_template'] = "Detected from history"

                # 2. Correspondence
                if (old_abs_path / 'correspondence').exists() and list((old_abs_path / 'correspondence').glob('*')):
                    prefill['prev_correspondence'] = list((old_abs_path / 'correspondence').glob('*'))[0].name
                elif list(old_abs_path.glob("*.csv")):
                    prefill['prev_correspondence'] = "Detected from history"

                # 3. Zip
                zips = [z for z in old_abs_path.glob("*.zip") if "tout_telecharger" not in z.name]
                if zips: prefill['prev_zip'] = zips[0].name

                # 4. Primers (Optionnel)
                if (old_abs_path / 'primers').exists() and list((old_abs_path / 'primers').glob('*')):
                    prefill['prev_primers'] = list((old_abs_path / 'primers').glob('*'))[0].name
                elif [f for f in old_abs_path.glob("*.csv") if "primer" in f.name.lower()]: 
                    prefill['prev_primers'] = "Detected from history"

                # 5. Concentrations (Optionnel)
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

            # --- FICHIERS OPTIONNELS (CORRECTION LOGIQUE) ---
            # On récupère les flags de suppression
            clear_primers = request.POST.get('clear_primers') == 'true'
            clear_concentrations = request.POST.get('clear_concentrations') == 'true'

            # On appelle la fonction en passant le flag. 
            # La fonction gère maintenant l'ordre : Upload > Clear > Historique
            path_primers_db = handle_file_upload_or_recover(
                request, 'primers_file', 'primers', work_dir, old_path_src, clear_flag=clear_primers
            )
            
            path_conc = handle_file_upload_or_recover(
                request, 'concentrations_file', 'concentrations', work_dir, old_path_src, clear_flag=clear_concentrations
            )

            # Séquences
            sequences_dir = work_dir / 'sequences'
            sequences_dir.mkdir(exist_ok=True)
            use_collections = request.POST.get('use_collections') == 'on'
            zip_name_display = "sequences.zip"

            if use_collections:
                selected_ids = request.POST.getlist('selected_collections')
                if not selected_ids: raise Exception("No collection selected.")
                zip_name_display = "Collections (No Zip)"
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
                elif not use_collections:
                    raise Exception("No sequence source provided.")

            # --- PARAMÈTRES TEXTE ---
            pcr_primers = []
            if request.POST.get('pcr_primers'):
                for line in request.POST.get('pcr_primers').splitlines():
                    if ',' in line: pcr_primers.append(tuple(x.strip() for x in line.split(',')[:2]))

            enzymes = [e.strip() for e in request.POST.get('digestion_enzymes', '').split(',') if e.strip()] or None
            def_conc = float(request.POST.get('default_concentration', 200))

            # --- SÉCURITÉ ANTI-CRASH ---
            # Si le fichier d'amorces a été supprimé (via Remove) et pas remplacé, 
            # on doit vider la liste des paires, sinon InSillyClo plante.
            if not path_primers_db:
                pcr_primers = []

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
                new_campaign = Campaign.objects.create(
                    name=request.POST.get('simulation_name') or "Untitled",
                    owner=request.user,
                    run_id=sim_id,
                    input_file=relative_input_path,
                    parameters={
                        'pcr_primers_text': request.POST.get('pcr_primers', ''),
                        'digestion_enzymes': request.POST.get('digestion_enzymes', ''),
                        'default_concentration': def_conc,
                        'use_collections': use_collections,
                        
                        'template_name': path_template.name,
                        'correspondence_name': path_mapping.name,
                        'archive_name': zip_name_display,
                        'primers_name': path_primers_db.name if path_primers_db else None,
                        'concentrations_name': path_conc.name if path_conc else None
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
    campaigns = Campaign.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'simulations/history.html', {'campaigns': campaigns})

# --- 3. DÉTAILS / RÉSULTATS ---
def simulation_detail_view(request, sim_id):
    campaign = None
    try:
        campaign = Campaign.objects.get(run_id=sim_id)
    except Campaign.DoesNotExist:
        pass

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
        'output_dir_url': f"{settings.MEDIA_URL}simulations/{sim_id}/results",
        'zip_url': f"{settings.MEDIA_URL}simulations/{sim_id}/tout_telecharger.zip" if os.path.exists(os.path.join(sim_abs_path, 'tout_telecharger.zip')) else None
    }
    
    context = {
        'results': results,
        'campaign': campaign
    }
    
    return render(request, 'simulations/simulation_results.html', context)