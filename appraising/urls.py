from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('appraisals/', views.list_appraisals, name='list'),
    path('appraisals/<int:id>/', views.detail, name='detail'),
    path('appraisals/add/', views.add_appraisal, name='add'),
    path('appraisals/<int:id>/close/', views.close_appraisal, name='close_appraisal'),
    path('search/', views.search, name='search'),
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/<int:id>/', views.tag_detail, name='tag_detail'),
    path('stats/', views.stats, name='stats'),
]
