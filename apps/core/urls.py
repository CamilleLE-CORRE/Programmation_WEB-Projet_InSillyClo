from django.urls import path
from .views import HomeView, AdminOnlyView

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin-dashboard/", AdminOnlyView.as_view(), name="admin_dashboard"),

]


