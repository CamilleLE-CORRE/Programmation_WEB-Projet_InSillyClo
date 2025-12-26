"""
views 的每一个app对用哪个URL；
--login
--singup

"""

from django.urls import path
from . import views 
from django.contrib.auth import views as auth_views

url