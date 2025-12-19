"""
Docstring for apps.accounts.views
Define views for user account management, including login, logout, registration, and profile views."""

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect



def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("core:home")
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("core:home")


def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("core:home")
    else:
        form = UserCreationForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html")
