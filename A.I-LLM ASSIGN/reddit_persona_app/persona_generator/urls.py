# persona_generator/urls.py

from django.urls import path
from . import views

app_name = 'persona_generator' # Namespace for your app

urlpatterns = [
    path('', views.index, name='index'), # Home page with form and list
    path('persona/<int:pk>/', views.persona_detail, name='persona_detail'), # Detail page for a persona
    path('generate_persona/', views.generate_persona, name='generate_persona'), # API endpoint for generation
]