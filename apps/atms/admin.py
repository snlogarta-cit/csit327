"""
ATM Social Map — Django Admin Registration
============================================
Registers ATM, Tag, and ATMStatusReport with the Django admin site.
The ATM model uses a GIS-aware ModelAdmin (GeoModelAdmin) to render
an OpenLayers map widget for the location PointField.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import ATM, ATMStatusReport, Tag


@admin.register(ATM)
class ATMAdmin(GISModelAdmin):
    """Admin view for ATMs with an interactive map widget for the location field."""

    list_display  = ['name', 'bank', 'address', 'created_by', 'created_at']
    list_filter   = ['bank', 'created_at']
    search_fields = ['name', 'address', 'created_by__username']
    readonly_fields = ['created_at']
    ordering      = ['-created_at']

    # GISModelAdmin renders an OpenLayers map widget for the PointField
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 13,
            'default_lon':  121.0,   # Manila longitude
            'default_lat':  14.58,   # Manila latitude
        }
    }


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ATMStatusReport)
class ATMStatusReportAdmin(admin.ModelAdmin):
    list_display  = ['atm', 'status', 'user', 'created_at']
    list_filter   = ['status', 'created_at']
    search_fields = ['atm__name', 'user__username', 'note']
    readonly_fields = ['created_at']
    filter_horizontal = ['tags']
    ordering = ['-created_at']
