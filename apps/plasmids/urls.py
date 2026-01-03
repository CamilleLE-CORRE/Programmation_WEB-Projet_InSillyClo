from django.urls import path
from .views import PlasmidSearchView

app_name = "plasmids"
urlpatterns = [
    path("search/", PlasmidSearchView.as_view(), name="search"),
]
