from django.urls import path
from . import views

app_name = "publications"

urlpatterns = [
    # User publication request views
    path(
        "request/<str:target_kind>/<int:target_id>/",
        views.request_publication,
        name="request_publication",
    ),

    path(
        "my/",
        views.my_publication_requests,
        name="my_requests",
    ),

    # Admin publication review views
    path(
        "admin/requests/",
        views.admin_publication_requests,
        name="admin_requests",
    ),

    path(
        "admin/review/<int:publication_id>/",
        views.admin_review_publication_request,
        name="admin_review",
    ),
]
