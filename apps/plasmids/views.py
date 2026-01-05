from django.shortcuts import render
from django.views.generic import TemplateView


class PlasmidSearchView(TemplateView):
    template_name = "plasmids/search.html"
