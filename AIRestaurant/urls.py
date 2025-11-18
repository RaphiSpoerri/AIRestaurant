"""
URL configuration for AIRestaurant project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from . import views
def template(name):
    return path(name, lambda request: render(request, name + ".html"), name=name)

urlpatterns = [
    path('', views.home, name='home'),
    path("admin/", admin.site.urls),
    path('index/', views.home, name='index'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),

    template('ai_chat'),
    path('ai_chat_query/<str:question>/', views.ai_chat, name='ai_chat_query'),
    template('cart'),
    template('order_history'),
    template('deposit'),
    template('file_complaint'),
    template('file_compliment'),
    template('chef_dashboard'),
    template('available_orders'),
    template('my_deliveries'),
    template('manager_dashboard'),
    template('manage_menu'),
    template('logout'),
    template('login'),
    template('register')
]
