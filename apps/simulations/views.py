from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
import zipfile
import pandas as pd
from .models import Campaign, CampaignResult
from django.db.models import Count
from apps.campaigns.models import CampaignTemplate
from apps.plasmids.models import PlasmidCollection
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

# from .forms import SimulationForm
# from .utils.insillyclo_wrapper import InSillyCloPipeline

class SimulationListView(LoginRequiredMixin, TemplateView):
    template_name = "simulations/simu.html"
    login_url = reverse_lazy("accounts:login")


@login_required(login_url=reverse_lazy("accounts:login"))
@require_http_methods(["GET", "POST"])
def simulation_view(request):
    """
    Handle campaign simulation requests.
    GET: Display the simulation form
    POST: Process the simulation
    """
    context = {}
    
    # If user is authenticated, get their collections
    if request.user.is_authenticated:
        context['user_collections'] = PlasmidCollection.objects.filter(
            owner=request.user,
            is_public=False
        ).annotate(plasmid_count=Count('plasmids'))
        
    # Get public collections
    context['public_collections'] = PlasmidCollection.objects.filter(
        is_public=True
    ).annotate(plasmid_count=Count('plasmids'))
    
    if request.method == 'POST':
        return handle_simulation_post(request, context)
    
    return render(request, 'simulations/simulation_form.html', context)


def handle_simulation_post(request, context):
    """Process the simulation POST request"""
    
    # Validate required files
    if 'template_file' not in request.FILES:
        messages.error(request, "Campaign template file is required.")
        return render(request, 'simulations/simulation_form.html', context)
    
    # Check if using collections or archive
    use_collections = request.POST.get('use_collections') == 'on'
    
    if not use_collections and 'sequences_archive' not in request.FILES:
        messages.error(request, "Plasmid sequences archive is required when not using collections.")
        return render(request, 'simulations/simulation_form.html', context)
    
    try:
        # Create temporary directory for processing
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='insillyclo_sim_')
        
        # Save uploaded files
        template_file = request.FILES['template_file']
        template_path = save_uploaded_file(template_file, temp_dir)
        
        sequences_paths = []
        
        # Handle sequences from archive or collections
        if use_collections:
            selected_collections = request.POST.getlist('selected_collections')
            sequences_paths = export_collections_to_genbank(selected_collections, temp_dir)
        else:
            sequences_archive = request.FILES['sequences_archive']
            sequences_path = extract_sequences_archive(sequences_archive, temp_dir)
            sequences_paths.append(sequences_path)
        
        # Handle correspondence file
        correspondence_path = None
        if 'correspondence_file' in request.FILES:
            correspondence_file = request.FILES['correspondence_file']
            correspondence_path = save_uploaded_file(correspondence_file, temp_dir)
        
        # Gather optional parameters
        optional_params = gather_optional_parameters(request)
        
        # Run the simulation
        # pipeline = InSillyCloPipeline(
        #     template_path=template_path,
        #     sequences_paths=sequences_paths,
        #     correspondence_path=correspondence_path,
        #     **optional_params
        # )
        
        #results = pipeline.run()
        
        # Save results if requested
        # if request.user.is_authenticated and request.POST.get('save_results') == 'on':
        #     save_simulation_results(request.user, results, request.POST.get('simulation_name'))
        
        # Store results in session for display
        #request.session['simulation_results'] = results
        
        messages.success(request, "Simulation completed successfully!")
        return redirect('simulations:simulation_results')
        
    except Exception as e:
        messages.error(request, f"Simulation failed: {str(e)}")
        return render(request, 'simulations/simulation_form.html', context)
    
    finally:
        # Cleanup temporary files
        if 'temp_dir' in locals():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def save_uploaded_file(uploaded_file, directory):
    """Save an uploaded file to the specified directory"""
    fs = FileSystemStorage(location=directory)
    filename = fs.save(uploaded_file.name, uploaded_file)
    return os.path.join(directory, filename)


def extract_sequences_archive(archive_file, directory):
    """Extract a ZIP archive of GenBank files"""
    sequences_dir = os.path.join(directory, 'sequences')
    os.makedirs(sequences_dir, exist_ok=True)
    
    with zipfile.ZipFile(archive_file, 'r') as zip_ref:
        # Extract only .gb files
        for member in zip_ref.namelist():
            if member.endswith('.gb'):
                zip_ref.extract(member, sequences_dir)
    
    return sequences_dir


def export_collections_to_genbank(collection_ids, directory):
    """Export plasmids from collections to GenBank files"""
    sequences_dir = os.path.join(directory, 'sequences')
    os.makedirs(sequences_dir, exist_ok=True)
    
    collections = PlasmidCollection.objects.filter(id__in=collection_ids)
    
    for collection in collections:
        for plasmid in collection.plasmids.all():
            filename = f"{plasmid.identifier}.gb"
            filepath = os.path.join(sequences_dir, filename)
            
            # Write GenBank content
            with open(filepath, 'w') as f:
                f.write(plasmid.genbank_content)
    
    return [sequences_dir]


def gather_optional_parameters(request):
    """Extract optional parameters from POST request"""
    params = {}
    
    # PCR primers
    if request.POST.get('pcr_primers'):
        primers = request.POST.get('pcr_primers').strip().split('\n')
        params['pcr_primers'] = [p.strip() for p in primers if p.strip()]
    
    # Digestion enzymes
    if request.POST.get('digestion_enzymes'):
        enzymes = request.POST.get('digestion_enzymes').strip().split(',')
        params['digestion_enzymes'] = [e.strip() for e in enzymes if e.strip()]
    
    # Concentrations file
    if 'concentrations_file' in request.FILES:
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        for chunk in request.FILES['concentrations_file'].chunks():
            temp_file.write(chunk)
        temp_file.close()
        params['concentrations_file'] = temp_file.name
    
    # Default concentration
    if request.POST.get('default_concentration'):
        params['default_concentration'] = float(request.POST.get('default_concentration'))
        params['concentration_unit'] = request.POST.get('concentration_unit', 'ng/µL')
    
    # Dilution parameters
    if request.POST.get('target_volume'):
        params['target_volume'] = float(request.POST.get('target_volume'))
    
    if request.POST.get('target_concentration'):
        params['target_concentration'] = float(request.POST.get('target_concentration'))
    
    params['equimolar_mix'] = request.POST.get('equimolar_mix') == 'on'
    
    # Notes
    if request.POST.get('notes'):
        params['notes'] = request.POST.get('notes')
    
    return params


def save_simulation_results(user, results, simulation_name):
    """Save simulation results to database"""
    simulation = Simulation.objects.create(
        user=user,
        name=simulation_name,
        results_data=results,
        status='completed'
    )
    
    # Optionally save generated plasmids
    if 'generated_plasmids' in results:
        for plasmid_data in results['generated_plasmids']:
            # Create plasmid objects that can be added to collections
            pass
    
    return simulation

def simulation_results_view(request):
    """
    Display simulation results
    """
    # results = request.session.get('simulation_results')
    return render(request, 'simulations/simulation_results.html')


def simulation_detail_view(request, sim_id):
    """
    Display details of a specific simulation
    """
    return render(
        request,
        'simulations/simulation_detail.html',
        {'sim_id': sim_id}
    )

