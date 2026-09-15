"""
ATM Social Map — URL Configuration
=====================================
All API endpoints are namespaced under /api/atms/.

  GET  /api/atms/          → ATMListView       (all ATMs as GeoJSON)
  GET  /api/atms/nearby/   → ATMNearbyView     (proximity filter)
  POST /api/atms/report/   → ATMReportView     (crowd status update)
  POST /api/atms/add/      → ATMAddView        (add new ATM pin)
  GET  /api/atms/tags/     → TagListView       (available tags)
"""

from django.urls import path

from .views import ATMAddView, ATMListView, ATMNearbyView, ATMReportView, TagListView

app_name = 'atms'

urlpatterns = [
    path('',        ATMListView.as_view(),   name='atm-list'),
    path('nearby/', ATMNearbyView.as_view(), name='atm-nearby'),
    path('report/', ATMReportView.as_view(), name='atm-report'),
    path('add/',    ATMAddView.as_view(),    name='atm-add'),
    path('tags/',   TagListView.as_view(),   name='tag-list'),
]
