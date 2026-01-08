from django.shortcuts import render
from django.views.generic import TemplateView
from .models import Plasmid, PlasmidCollection


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

class PlasmidList(TemplateView):
    template_name = "plasmids/plasmid_list.html"

def plasmid_list(request):
    if request.user.is_authenticated:
        plasmids = Plasmid.objects.filter(
            collection__is_public=True
        ) | Plasmid.objects.filter(
            collection__owner=request.user
        )
    else:
        plasmids = Plasmid.objects.filter(collection__is_public=True)
    
    
    return render(request, 'plasmids/list.html', {
        'plasmids': plasmids.distinct()
    })
