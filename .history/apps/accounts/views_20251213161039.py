"""
Docstring for apps.accounts.views
Define views for user account management, including login, logout, registration, and profile views."""

from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
