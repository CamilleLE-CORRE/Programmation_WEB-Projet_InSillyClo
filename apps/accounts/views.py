from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model
User = get_user_model()
from django.views.generic import UpdateView
from .forms import SignUpForm, EmailAuthenticationForm, ProfileForm


# Authentification utilisateur par email
# Affichage du formulaire de connexion
class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"

# Déconnexion utilisateur
# Redirection vers la page de login
class EmailLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

# Création de compte utilisateur
# Affichage du formulaire d’inscription
# Enregistrement en base
# Redirection vers la page de login après inscription réussie
class SignUpView(CreateView):
    model = User
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

# Affichage du profil utilisateur
# Accès restreint aux utilisateurs connectés
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

# Modification du profil utilisateur
# Édition des informations du compte connecté
# Mise à jour en base
class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user
  

