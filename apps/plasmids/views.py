from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Plasmid, PlasmidCollection


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

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
