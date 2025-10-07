from django.urls import path
from . import views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('core/dashboard/', views.dashboard, name='dashboard'),
    path('', RedirectView.as_view(pattern_name='usuarios:login', permanent=False), name='index'),
]

