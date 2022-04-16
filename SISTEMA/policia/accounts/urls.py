
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home),
    path('registro/', views.registro),
    path('consulta/', views.consulta),
  
]