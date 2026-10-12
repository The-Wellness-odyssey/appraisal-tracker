from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('appraisals/', views.list_appraisals, name='list'),
    path('appraisals/<int:id>/', views.detail, name='detail'),
    path('appraisals/add/', views.add_appraisal, name='add'),
    path('stats/', views.stats, name='stats'),
]