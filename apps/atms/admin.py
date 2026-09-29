"""
ATM Social Map — Django Admin Registration
============================================
Registers Bank, CardNetwork, NetworkAlliance, ATM, ATMNetwork, StatusReport,
and ATMReport with the Django admin site.
"""

from django.contrib import admin

from .models import (
    ATM,
    ATMNetwork,
    ATMReport,
    Bank,
    CardNetwork,
    NetworkAlliance,
    StatusReport,
)

try:
    from django.contrib.gis.admin import GISModelAdmin
    BaseATMAdmin = GISModelAdmin
except Exception:
    BaseATMAdmin = admin.ModelAdmin


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ['bank_id', 'bank_name', 'logo_url']
    search_fields = ['bank_name']


@admin.register(CardNetwork)
class CardNetworkAdmin(admin.ModelAdmin):
    list_display = ['network_id', 'network_name', 'logo_url']
    search_fields = ['network_name']


@admin.register(NetworkAlliance)
class NetworkAllianceAdmin(admin.ModelAdmin):
    list_display = ['alliance_id', 'bank', 'card_network', 'is_fee_free', 'surcharge_amt']
    list_filter = ['is_fee_free', 'bank', 'card_network']
    search_fields = ['bank__bank_name', 'card_network__network_name']


class ATMNetworkInline(admin.TabularInline):
    model = ATMNetwork
    extra = 1


@admin.register(ATM)
class ATMAdmin(BaseATMAdmin):
    """Admin view for ATMs."""

    list_display = ['atm_id', 'name', 'bank', 'latitude', 'longitude', 'is_active', 'created_at', 'updated_at']
    list_filter = ['bank', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'address_line', 'bank__bank_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [ATMNetworkInline]

    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 13,
            'default_lon': 121.0,
            'default_lat': 14.58,
        }
    }


@admin.register(ATMNetwork)
class ATMNetworkAdmin(admin.ModelAdmin):
    list_display = ['atm_network_id', 'atm', 'network']
    search_fields = ['atm__name', 'network__network_name']
    list_filter = ['network']


@admin.register(StatusReport)
class StatusReportAdmin(admin.ModelAdmin):
    list_display = ['status_report_id', 'atm', 'user', 'is_online', 'has_cash', 'created_at', 'updated_at']
    list_filter = ['is_online', 'has_cash', 'created_at', 'updated_at']
    search_fields = ['atm__name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ATMReport)
class ATMReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'atm', 'user', 'report_type', 'actual_fee', 'created_at', 'updated_at']
    list_filter = ['report_type', 'created_at', 'updated_at']
    search_fields = ['atm__name', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
