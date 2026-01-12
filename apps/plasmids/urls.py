from django.urls import path
from .views import PlasmidSearchView, plasmid_list, plasmid_detail

app_name = "plasmids"
urlpatterns = [
    path("plasmid_list/", plasmid_list, name="plasmid_list"),
    path("<str:identifier>/", plasmid_detail, name="plasmid_detail"),
    path("search/", PlasmidSearchView.as_view(), name="search"),
]
