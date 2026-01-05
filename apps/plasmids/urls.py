from django.urls import path
from .views import PlasmidSearchView
from .views import PlasmidList

app_name = "plasmids"
urlpatterns = [
    path("search/", PlasmidSearchView.as_view(), name="search"),
    path("plasmid_list/", PlasmidList.as_view(), name="plasmid_list"),
]
