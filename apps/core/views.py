from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model

class HomeView(TemplateView):
    template_name = "core/home.html"

from apps.campaigns.models import CampaignTemplate   

class AdminOnlyView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/admin_page.html"

    def test_func(self):
        return self.request.user.is_staff


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_count"] = get_user_model().objects.count()
        context["template_count"] = CampaignTemplate.objects.count()
        return context