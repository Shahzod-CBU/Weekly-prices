from django.urls import path
from . import views
from django.conf.urls import url

urlpatterns = [
    path('', views.index, name='index'),
    path('changes/', views.changes, name='changes'),
    path('by_regions/', views.by_regions, name='by_regions'),
    path('by_regions/by_regions_update/', views.by_regions_update, name='by_regions_update'),
    path('changes/change_button/', views.change_button, name='change_button'),
    path('changes/save_price', views.save_price, name='save_price'),
    path('save_price', views.save_price, name='save_price'),
    path('change_date/', views.change_date, name='change_date'),
    path('export_prices/', views.export_prices, name='export_prices'),
    path('export_changes/', views.export_changes, name='export_changes'),
    path('export_by_region/', views.export_by_region, name='export_by_region'),
    path('changes/get_details/', views.get_details, name='get_details'),
]