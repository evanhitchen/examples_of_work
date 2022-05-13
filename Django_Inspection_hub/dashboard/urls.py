from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('client_info/<str:pk>/', views.client_info, name='client_info'),
    path('site_info/<str:pk>/', views.site_info, name='site_info'),
    path('create_client/', views.create_client, name='create_client'),
    path('create_site/', views.create_site, name='create_site'),
    path('create_structure/', views.create_structure, name='create_structure'),
    path('update_client/<str:pk_test>/', views.update_client, name='update_client'),
    path('update_site/<str:pk_test>/', views.update_site, name='update_site'),
    path('update_structure/<str:pk_test>/', views.update_structure, name='update_structure'),
    path('select_client/', views.select_client, name='select_client'),
    path('upload_R8R9/', views.upload_r8r9, name='uploadr8r9'),
    path('upload_excel/', views.upload_excel, name='uploadexcel'),
    path('select_structure_for_R8R9/', views.select_structure_for_R8R9, name='select_r8r9'),
    path('view_r8r9_output/<str:pk>/', views.view_r8r9, name='view_r8r9'),
    path('maps/', views.map, name='map'),
]