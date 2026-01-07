from django.urls import path
from . import views
from .views import SimulationListView

app_name = "simulations"

urlpatterns = [
    path("", SimulationListView.as_view(), name="simu"),
    path('simulations/', views.simulation_view, name='simulation'),
    path('simulations/results/', views.simulation_results_view, name='simulation_results'),
    path('simulations/<int:sim_id>/', views.simulation_detail_view, name='simulation_detail'),
]
