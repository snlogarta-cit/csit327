"""
ATM Social Map — DRF Serializers
==================================
Serializers bridge Django models to JSON / GeoJSON responses consumed by
the Leaflet.js frontend.

  ATMGeoSerializer        — GeoJSON FeatureCollection output for the map.
  TagSerializer           — Lightweight tag representation.
  ATMStatusReportSerializer — Validates and saves crowd status reports.
  ATMCreateSerializer     — Validates and saves new ATM pins from the map.
"""

from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import ATM, ATMStatusReport, Tag

User = get_user_model()


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tag
        fields = ['id', 'name', 'slug']


# ---------------------------------------------------------------------------
# ATM — GeoJSON output (map pins)
# ---------------------------------------------------------------------------

class ATMGeoSerializer(GeoFeatureModelSerializer):
    """
    Outputs each ATM as a GeoJSON Feature with a Point geometry.
    Additional properties carry the ATM's latest crowd-sourced status,
    active tags, reporter username, and a human-readable relative time.

    Used by:
      GET /api/atms/
      GET /api/atms/nearby/
    """

    # Annotated / computed fields populated in the view queryset or here
    current_status      = serializers.SerializerMethodField()
    current_status_label = serializers.SerializerMethodField()
    active_tags         = serializers.SerializerMethodField()
    last_reported_at    = serializers.SerializerMethodField()
    last_reported_by    = serializers.SerializerMethodField()
    bank_display        = serializers.CharField(source='get_bank_display', read_only=True)
    report_count        = serializers.SerializerMethodField()

    class Meta:
        model          = ATM
        geo_field      = 'location'         # PostGIS PointField → GeoJSON geometry
        fields         = [
            'id',
            'name',
            'bank',
            'bank_display',
            'address',
            'current_status',
            'current_status_label',
            'active_tags',
            'last_reported_at',
            'last_reported_by',
            'report_count',
            'created_at',
        ]

    def _get_latest_report(self, obj):
        """
        Return the most recent ATMStatusReport for this ATM.
        Uses prefetched data when available to avoid N+1 queries.
        """
        if hasattr(obj, '_latest_report'):
            return obj._latest_report
        return obj.status_reports.order_by('-created_at').select_related('user').prefetch_related('tags').first()

    def get_current_status(self, obj):
        report = self._get_latest_report(obj)
        return report.status if report else 'UNKNOWN'

    def get_current_status_label(self, obj):
        report = self._get_latest_report(obj)
        return report.get_status_display() if report else 'No reports yet'

    def get_active_tags(self, obj):
        report = self._get_latest_report(obj)
        if report:
            return TagSerializer(report.tags.all(), many=True).data
        return []

    def get_last_reported_at(self, obj):
        """Return a relative time string, e.g. '5 minutes ago'."""
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
# ATM Status Report — write (POST /api/atms/report/)
# ---------------------------------------------------------------------------

class ATMStatusReportSerializer(serializers.ModelSerializer):
    """
    Accepts a crowd-sourced status update from an authenticated user.
    Tags are accepted as a list of tag IDs.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model  = ATMStatusReport
        fields = ['id', 'atm', 'status', 'note', 'tags', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_atm(self, value):
        if not ATM.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError('ATM does not exist.')
        return value

    def create(self, validated_data):
        # `user` is injected from request in the view's perform_create
        tags = validated_data.pop('tags', [])
        report = ATMStatusReport.objects.create(**validated_data)
        report.tags.set(tags)
        return report


# ---------------------------------------------------------------------------
# ATM — write (POST /api/atms/add/)
# ---------------------------------------------------------------------------

class ATMCreateSerializer(serializers.ModelSerializer):
    """
    Accepts a new ATM submission from the map click-to-add modal.
    Coordinates arrive as plain lat/lng floats and are converted to a
    PostGIS Point before saving.
    """

    latitude  = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)

    class Meta:
        model  = ATM
        fields = ['id', 'name', 'bank', 'address', 'latitude', 'longitude']
        read_only_fields = ['id']

    def validate(self, attrs):
        lat = attrs.pop('latitude')
        lng = attrs.pop('longitude')
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError({'latitude': 'Must be between -90 and 90.'})
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError({'longitude': 'Must be between -180 and 180.'})
        from django.contrib.gis.geos import Point
        attrs['location'] = Point(lng, lat, srid=4326)  # Point(x=lon, y=lat)
        return attrs

    def create(self, validated_data):
        # `created_by` is injected from request in the view's perform_create
        return ATM.objects.create(**validated_data)
