"""
ATM Social Map — DRF Serializers
==================================
Serializers bridge Django models to JSON / GeoJSON responses consumed by
the Leaflet.js frontend.
"""

from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers

try:
    from rest_framework_gis.serializers import GeoFeatureModelSerializer
    HAS_DRF_GIS = True
except Exception:
    GeoFeatureModelSerializer = serializers.ModelSerializer
    HAS_DRF_GIS = False

from .models import ATM, ATMNetwork, ATMReport, Bank, CardNetwork, NetworkAlliance, StatusReport

User = get_user_model()


# ---------------------------------------------------------------------------
# Bank & CardNetwork Serializers
# ---------------------------------------------------------------------------

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['bank_id', 'bank_name', 'logo_url']


class CardNetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardNetwork
        fields = ['network_id', 'network_name', 'logo_url']


class NetworkAllianceSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.bank_name', read_only=True)
    card_network_name = serializers.CharField(source='card_network.network_name', read_only=True)

    class Meta:
        model = NetworkAlliance
        fields = ['alliance_id', 'bank', 'bank_name', 'card_network', 'card_network_name', 'is_fee_free', 'surcharge_amt']


# ---------------------------------------------------------------------------
# ATM — GeoJSON output (map pins)
# ---------------------------------------------------------------------------

class ATMGeoSerializer(GeoFeatureModelSerializer):
    """
    Outputs each ATM with coordinates, latest crowd-sourced status,
    reporter username, bank name, networks, and a human-readable relative time.
    """

    bank_id = serializers.IntegerField(source='bank.bank_id', read_only=True)
    bank_name = serializers.CharField(source='bank.bank_name', read_only=True)
    bank_logo_url = serializers.CharField(source='bank.logo_url', read_only=True)
    current_status = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    has_cash = serializers.SerializerMethodField()
    last_reported_at = serializers.SerializerMethodField()
    last_reported_by = serializers.SerializerMethodField()
    report_count = serializers.SerializerMethodField()
    networks = CardNetworkSerializer(many=True, read_only=True)

    class Meta:
        model = ATM
        if HAS_DRF_GIS and hasattr(ATM, 'location'):
            geo_field = 'location'
        fields = [
            'atm_id',
            'name',
            'bank_id',
            'bank_name',
            'bank_logo_url',
            'latitude',
            'longitude',
            'address_line',
            'is_active',
            'current_status',
            'is_online',
            'has_cash',
            'last_reported_at',
            'last_reported_by',
            'report_count',
            'networks',
            'created_at',
            'updated_at',
        ]

    def _get_latest_report(self, obj):
        if hasattr(obj, '_latest_report'):
            return obj._latest_report
        return obj.status_reports.order_by('-created_at').select_related('user').first()

    def get_current_status(self, obj):
        report = self._get_latest_report(obj)
        if not report:
            return 'UNKNOWN'
        if report.is_online and report.has_cash:
            return 'ONLINE'
        if report.is_online and not report.has_cash:
            return 'NO_CASH'
        return 'OFFLINE'

    def get_is_online(self, obj):
        report = self._get_latest_report(obj)
        return report.is_online if report else None

    def get_has_cash(self, obj):
        report = self._get_latest_report(obj)
        return report.has_cash if report else None

    def get_last_reported_at(self, obj):
        report = self._get_latest_report(obj)
        if not report:
            return None
        delta = now() - report.created_at
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f'{seconds}s ago'
        minutes = seconds // 60
        if minutes < 60:
            return f'{minutes}m ago'
        hours = minutes // 60
        if hours < 24:
            return f'{hours}h ago'
        return f'{delta.days}d ago'

    def get_last_reported_by(self, obj):
        report = self._get_latest_report(obj)
        return report.user.username if report else None

    def get_report_count(self, obj):
        return obj.status_reports.count()


# ---------------------------------------------------------------------------
# Status Report — write (POST /api/atms/report/)
# ---------------------------------------------------------------------------

class StatusReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusReport
        fields = ['status_report_id', 'atm', 'is_online', 'has_cash', 'created_at', 'updated_at']
        read_only_fields = ['status_report_id', 'created_at', 'updated_at']

    def validate_atm(self, value):
        if not ATM.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError('ATM does not exist.')
        return value


# ---------------------------------------------------------------------------
# ATM Report — write
# ---------------------------------------------------------------------------

class ATMReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATMReport
        fields = [
            'report_id',
            'atm',
            'report_type',
            'actual_fee',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['report_id', 'created_at', 'updated_at']

    def validate_atm(self, value):
        if not ATM.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError('ATM does not exist.')
        return value


# ---------------------------------------------------------------------------
# ATM — write (POST /api/atms/add/)
# ---------------------------------------------------------------------------

class ATMCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    network_ids = serializers.PrimaryKeyRelatedField(
        queryset=CardNetwork.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = ATM
        fields = [
            'atm_id',
            'name',
            'bank',
            'address_line',
            'latitude',
            'longitude',
            'is_active',
            'network_ids',
        ]
        read_only_fields = ['atm_id']

    def validate(self, attrs):
        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        if not (-90 <= float(lat) <= 90):
            raise serializers.ValidationError({'latitude': 'Must be between -90 and 90.'})
        if not (-180 <= float(lng) <= 180):
            raise serializers.ValidationError({'longitude': 'Must be between -180 and 180.'})
        return attrs

    def create(self, validated_data):
        networks = validated_data.pop('network_ids', [])
        atm = ATM.objects.create(**validated_data)
        if networks:
            atm.networks.set(networks)
        return atm
