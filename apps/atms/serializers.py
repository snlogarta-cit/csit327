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
    bank_display = serializers.CharField(source='bank.bank_name', read_only=True)
    bank_logo_url = serializers.CharField(source='bank.logo_url', read_only=True)
    address = serializers.CharField(source='address_line', read_only=True)
    current_status = serializers.SerializerMethodField()
    current_status_label = serializers.SerializerMethodField()
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
            'bank_display',
            'bank_logo_url',
            'latitude',
            'longitude',
            'address_line',
            'address',
            'is_active',
            'current_status',
            'current_status_label',
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

    def get_current_status_label(self, obj):
        status = self.get_current_status(obj)
        labels = {
            'ONLINE': 'Online / Operational',
            'NO_CASH': 'No Cash',
            'OFFLINE': 'Offline / Out of Service',
            'UNKNOWN': 'Status Unknown',
        }
        return labels.get(status, 'Status Unknown')

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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not HAS_DRF_GIS or not hasattr(instance, 'location') or instance.location is None:
            # Format as GeoJSON Feature dictionary when DRF-GIS is inactive or location is null
            lat = float(instance.latitude) if instance.latitude is not None else None
            lng = float(instance.longitude) if instance.longitude is not None else None
            return {
                'id': instance.atm_id,
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lng, lat]
                } if lat is not None and lng is not None else None,
                'properties': ret
            }
        return ret


# ---------------------------------------------------------------------------
# Status Report — write (POST /api/atms/report/)
# ---------------------------------------------------------------------------

class StatusReportSerializer(serializers.ModelSerializer):
    status = serializers.CharField(write_only=True, required=False)
    is_online = serializers.BooleanField(required=False)
    has_cash = serializers.BooleanField(required=False)

    class Meta:
        model = StatusReport
        fields = ['status_report_id', 'atm', 'is_online', 'has_cash', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status_report_id', 'created_at', 'updated_at']

    def validate_atm(self, value):
        if not ATM.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError('ATM does not exist.')
        return value

    def validate(self, attrs):
        status_val = attrs.pop('status', None)
        if status_val:
            s = str(status_val).strip().upper()
            if s == 'ONLINE':
                attrs.setdefault('is_online', True)
                attrs.setdefault('has_cash', True)
            elif s == 'NO_CASH':
                attrs.setdefault('is_online', True)
                attrs.setdefault('has_cash', False)
            elif s == 'OFFLINE':
                attrs.setdefault('is_online', False)
                attrs.setdefault('has_cash', False)
            else:
                raise serializers.ValidationError({'status': f"Invalid status: '{status_val}'. Must be ONLINE, NO_CASH, or OFFLINE."})

        if 'is_online' not in attrs:
            raise serializers.ValidationError({'is_online': 'This field is required.'})
        if 'has_cash' not in attrs:
            raise serializers.ValidationError({'has_cash': 'This field is required.'})

        return attrs


# ---------------------------------------------------------------------------
# ATM Report — write
# ---------------------------------------------------------------------------

class ATMReportSerializer(serializers.ModelSerializer):
    report_type = serializers.CharField()
    note = serializers.CharField(write_only=True, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ATMReport
        fields = [
            'report_id',
            'atm',
            'report_type',
            'actual_fee',
            'comment',
            'note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['report_id', 'created_at', 'updated_at']

    def validate_atm(self, value):
        if not ATM.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError('ATM does not exist.')
        return value

    def validate_report_type(self, value):
        mapping = {
            'fee': ATMReport.ReportType.FEE_DISCREPANCY,
            'fee_discrepancy': ATMReport.ReportType.FEE_DISCREPANCY,
            'location': ATMReport.ReportType.LOCATION_INACCURATE,
            'location_inaccurate': ATMReport.ReportType.LOCATION_INACCURATE,
            'inaccurate_info': ATMReport.ReportType.INACCURATE_INFO,
            'issue': ATMReport.ReportType.OTHER_ISSUE,
            'other_issue': ATMReport.ReportType.OTHER_ISSUE,
            'note': ATMReport.ReportType.GENERAL_NOTE,
            'general_note': ATMReport.ReportType.GENERAL_NOTE,
        }
        val_clean = str(value).strip().lower()
        if val_clean in mapping:
            return mapping[val_clean]
        val_upper = str(value).strip().upper()
        valid_choices = [c[0] for c in ATMReport.ReportType.choices]
        if val_upper in valid_choices:
            return val_upper
        raise serializers.ValidationError(f"Invalid report_type: '{value}'. Valid choices: {valid_choices}")

    def validate(self, attrs):
        note = attrs.pop('note', None)
        if note and not attrs.get('comment'):
            attrs['comment'] = note
        return attrs


# ---------------------------------------------------------------------------
# ATM — write (POST /api/atms/add/)
# ---------------------------------------------------------------------------

class ATMCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    address = serializers.CharField(write_only=True, required=False)
    address_line = serializers.CharField(required=False)
    network_ids = serializers.PrimaryKeyRelatedField(
        queryset=CardNetwork.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )
    networks = serializers.PrimaryKeyRelatedField(
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
            'address',
            'latitude',
            'longitude',
            'is_active',
            'network_ids',
            'networks',
        ]
        read_only_fields = ['atm_id']

    def validate(self, attrs):
        addr = attrs.pop('address', None)
        if addr and not attrs.get('address_line'):
            attrs['address_line'] = addr
        if not attrs.get('address_line'):
            raise serializers.ValidationError({'address_line': 'Address is required.'})

        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            raise serializers.ValidationError({'coordinates': 'Latitude and longitude must be valid numbers.'})

        if not (-90 <= lat_f <= 90):
            raise serializers.ValidationError({'latitude': 'Must be between -90 and 90.'})
        if not (-180 <= lng_f <= 180):
            raise serializers.ValidationError({'longitude': 'Must be between -180 and 180.'})

        networks_alt = attrs.pop('networks', None)
        if networks_alt and not attrs.get('network_ids'):
            attrs['network_ids'] = networks_alt

        return attrs

    def create(self, validated_data):
        networks = validated_data.pop('network_ids', [])
        atm = ATM.objects.create(**validated_data)
        if networks:
            atm.networks.set(networks)
        return atm
