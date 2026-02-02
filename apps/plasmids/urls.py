from django.urls import path
from .views import PlasmidSearchView, PlasmidSearchResultsView, plasmid_list, plasmid_detail,PlasmidImportView
#from .views import CollectionListView,MyCollectionListView,CollectionCreateView,CollectionDetailView,CollectionUpdateView,CollectionDeleteView
from . import views


app_name = "plasmids"
urlpatterns = [
    # Plasmide collections
    path("collections/", views.CollectionListView.as_view(), name="collection_list"),
    path("collections/mine/", views.MyCollectionListView.as_view(), name="collection_list_mine"),

    path("collections/create/", views.CollectionCreateView.as_view(), name="collection_create"),
    path("collections/<int:pk>/", views.CollectionDetailView.as_view(), name="collection_detail"),
    path("collections/<int:pk>/edit/", views.CollectionUpdateView.as_view(), name="collection_edit"),
    path("collections/<int:pk>/delete/", views.CollectionDeleteView.as_view(), name="collection_delete"),
    path("collections/<int:pk>/add-plasmids/", views.CollectionAddPlasmidsView.as_view(), name="collection_add_plasmids"),
    path("plasmids/import/", views.PlasmidImportView.as_view(), name="plasmid_import"),


    # Plasmide
    path("plasmid_list/", plasmid_list, name="plasmid_list"),
    path("search/", PlasmidSearchView.as_view(), name="search"),
    path("search/results/", PlasmidSearchResultsView.as_view(), name="search_results"),
    path("<str:identifier>/", plasmid_detail, name="plasmid_detail"),
    
]
