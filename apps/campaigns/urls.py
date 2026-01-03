from django.urls import path
from . import views

app_name = "campaigns"

urlpatterns = [
    path('', views.template_list, name='template_list'),
    path('create/', views.create_template, name='create_template'),
    path('download/<int:template_id>/', views.download_template, name='download_template'),
    path('public/<int:template_id>/download/', views.download_public_template, name='download_public_template'),
    path('templates/<int:template_id>/delete/', views.delete_template, name='delete_template'),
]

