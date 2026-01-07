from django.urls import path
from . import views

app_name = "correspondences"

urlpatterns = [
    path("", views.correspondence_list, name="list"),
    path("<int:pk>/", views.correspondence_detail, name="detail"),
    path("<int:pk>/upload", views.correspondence_upload, name="upload"),
    path("new", views.correspondence_create, name="create"),
]
