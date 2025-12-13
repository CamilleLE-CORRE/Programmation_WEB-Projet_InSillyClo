"""
Docstring for apps.accounts.views
Define views for user account management, including login, logout, registration, and profile views."""

from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import User

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return HttpResponseRedirect(reverse('home'))
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})
