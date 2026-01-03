from django.views.generic import TemplateView

class SimulationListView(TemplateView):
    template_name = "simulations/simu.html"
