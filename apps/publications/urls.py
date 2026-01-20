from django.urls import path
from . import views

app_name = "publications"

urlpatterns = [
    path(
        "admin/requests/",
        views.admin_requests_list,
        name="admin_requests_list",
    ),
    path(
        "admin/requests/<int:pk>/",
        views.admin_request_detail,
        name="admin_request_detail",
    ),
    path(
    "request/plasmid-collection/<int:pk>/",
    views.request_publication_collection,
    name="request_create",
),
]
