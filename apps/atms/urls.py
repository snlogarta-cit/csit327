"""
ATM Social Map — URL Configuration
=====================================
All API endpoints are namespaced under /api/atms/.
"""

from django.urls import path

from .views import (
    ATMAddView,
    ATMListView,
    ATMNearbyView,
    ATMReportCreateView,
    BankListView,
    CardNetworkListView,
    StatusReportView,
)

app_name = 'atms'

urlpatterns = [
    path('',             ATMListView.as_view(),         name='atm-list'),
    path('nearby/',      ATMNearbyView.as_view(),       name='atm-nearby'),
    path('report/',      StatusReportView.as_view(),    name='atm-status-report'),
    path('issues/',      ATMReportCreateView.as_view(), name='atm-issue-report'),
    path('add/',         ATMAddView.as_view(),          name='atm-add'),
    path('banks/',       BankListView.as_view(),        name='bank-list'),
    path('networks/',    CardNetworkListView.as_view(), name='network-list'),
]
