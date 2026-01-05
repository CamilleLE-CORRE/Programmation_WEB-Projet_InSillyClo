from django.urls import path
from .views import SimulationListView

app_name = "simulations"

urlpatterns = [
    path("", SimulationListView.as_view(), name="simu"),
]
