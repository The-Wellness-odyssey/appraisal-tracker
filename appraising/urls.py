from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('appraising/', views.appraisal_list, name='list'),
    path('appraising/<int:appraisal_id>/', views.appraisal_detail, name='detail'),
    path('stats/', views.stats, name='stats'),
]