from django.shortcuts import render
from django.views.generic import TemplateView


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"

class PlasmidList(TemplateView):
    template_name = "plasmids/plasmid_list.html"
