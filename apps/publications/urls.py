from django.urls import path
from . import views

app_name = "publications"

urlpatterns = [
    # User publication request views
    path("request/<str:target_kind>/<int:target_id>/",views.request_publication, name="request_publication"),
    path("my/",views.my_publication_requests, name="my_requests"),

    # Cheffe publication review views
    path("cheffe/requests/", views.cheffe_publication_requests, name="cheffe_requests"),
    path("cheffe/review/<int:publication_id>/", views.cheffe_review_publication_request, name="cheffe_review"),
    path("cheffe/<int:pk>/", views.cheffe_detail, name="cheffe_detail"),

    # Admin publication review views
    path("admin/requests/", views.admin_publication_requests, name="admin_requests"),
    path("admin/review/<int:publication_id>/", views.admin_review_publication_request, name="admin_review"),
    path("admin/<int:pk>/", views.admin_detail, name="admin_detail"),
    path("cheffe/requests/<int:publication_id>/review/", views.cheffe_review_publication_request, name="cheffe_review_publication_request"),

]