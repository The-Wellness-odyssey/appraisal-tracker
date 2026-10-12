from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('appraisals/', views.list_appraisals, name='list'),
    path('appraisals/<int:id>/', views.detail, name='detail'),
    path('appraisals/add/', views.add_appraisal, name='add'),
    path('appraisals/<int:id>/close/', views.close_appraisal, name='close_appraisal'),
    path('stats/', views.stats, name='stats'),
]