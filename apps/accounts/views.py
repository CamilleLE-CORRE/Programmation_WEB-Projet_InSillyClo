from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model

from .forms import SignUpForm, EmailAuthenticationForm

User = get_user_model()

class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"

class EmailLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password1"],
        )
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
