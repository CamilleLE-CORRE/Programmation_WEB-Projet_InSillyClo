from django.urls import path
from . import views

app_name = 'simulations'

urlpatterns = [
    path('', views.simulation_view, name='simu'),
    path('history/', views.simulation_history_view, name='history'),
    path('results/<str:sim_id>/', views.simulation_detail_view, name='simulation_detail'),
    path('delete/', views.delete_campaigns_view, name='delete_campaigns'),
]