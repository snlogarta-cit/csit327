"""
ATM Social Map — DRF API Views
================================
Three API endpoints power the Leaflet.js frontend:

  ATMListView   — GET  /api/atms/
                  Returns every ATM as a GeoJSON FeatureCollection.

  ATMNearbyView — GET  /api/atms/nearby/?lat=&lng=&radius=
                  Filters ATMs within `radius` metres (default 3 000 m)
                  using a PostGIS ST_DWithin spatial lookup and orders
                  results by ascending distance.

  ATMReportView — POST /api/atms/report/
                  Authenticated users submit a crowd status update.

  ATMAddView    — POST /api/atms/add/
                  Authenticated users add a new ATM pin from the map.

  TagListView   — GET  /api/atms/tags/
                  Returns all available tags for the report modal.
"""

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db.models import Prefetch
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ATM, ATMStatusReport, Tag
from .serializers import (
    ATMCreateSerializer,
    ATMGeoSerializer,
    ATMStatusReportSerializer,
    TagSerializer,
)


# ---------------------------------------------------------------------------
# Helper: build optimised ATM queryset with prefetched latest report
# ---------------------------------------------------------------------------

def _atm_queryset_with_latest_report():
    """
    Build an ATM queryset that prefetches the latest status report and its
    tags in two extra queries instead of N+1 per ATM.
    We attach `_latest_report` as a cached attribute via Python post-processing
    because Django's ORM cannot natively prefetch "first of ordered related".
    """
    return (
        ATM.objects
        .prefetch_related(
            Prefetch(
                'status_reports',
                queryset=ATMStatusReport.objects
                         .order_by('-created_at')
                         .select_related('user')
                         .prefetch_related('tags'),
                to_attr='_prefetched_reports',
            )
        )
    )


def _attach_latest_report(atm_list):
    """
    Attach `_latest_report` to each ATM instance from the prefetched list.
    Avoids hitting the database again for serializer method fields.
    """
    for atm in atm_list:
        reports = getattr(atm, '_prefetched_reports', [])
        atm._latest_report = reports[0] if reports else None
    return atm_list


# ---------------------------------------------------------------------------
# GET /api/atms/
# ---------------------------------------------------------------------------

class ATMListView(APIView):
    """
    Returns all ATMs as a GeoJSON FeatureCollection.
    Publicly readable; no authentication required.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        atms = list(_atm_queryset_with_latest_report())
        _attach_latest_report(atms)
        serializer = ATMGeoSerializer(atms, many=True, context={'request': request})
        # GeoFeatureModelSerializer.many=True already returns a FeatureCollection dict
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /api/atms/nearby/
# ---------------------------------------------------------------------------

class ATMNearbyView(APIView):
    """
    Returns ATMs within `radius` metres of (lat, lng), ordered by distance.

    Query parameters:
      lat    — latitude  (required)
      lng    — longitude (required)
      radius — search radius in metres (optional, default: 3000)
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            lat    = float(request.query_params['lat'])
            lng    = float(request.query_params['lng'])
        except (KeyError, ValueError, TypeError):
            return Response(
                {'error': 'Query parameters `lat` and `lng` are required and must be numeric.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            radius = float(request.query_params.get('radius', 3000))
        except (ValueError, TypeError):
            radius = 3000.0

        # Build a PostGIS Point (lon, lat) in SRID 4326
        user_location = Point(lng, lat, srid=4326)

        # ST_DWithin spatial lookup — uses PostGIS spatial index efficiently
        atms = list(
            _atm_queryset_with_latest_report()
            .filter(location__distance_lte=(user_location, Distance(m=radius)))
            .order_by('location')       # PostGIS orders by distance when filtered
        )
        _attach_latest_report(atms)

        serializer = ATMGeoSerializer(atms, many=True, context={'request': request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# POST /api/atms/report/
# ---------------------------------------------------------------------------

class ATMReportView(generics.CreateAPIView):
    """
    Authenticated users submit a crowd status report for an existing ATM.

    Request body (JSON):
      {
        "atm":    <int: ATM id>,
        "status": "ONLINE" | "NO_CASH" | "OFFLINE" | "LONG_LINE",
        "note":   "<optional text>",
        "tags":   [<tag id>, ...]
      }
    """

    serializer_class   = ATMStatusReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Inject the authenticated user so the frontend doesn't need to pass it
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# POST /api/atms/add/
# ---------------------------------------------------------------------------

class ATMAddView(generics.CreateAPIView):
    """
    Authenticated users add a new ATM pin from the click-to-add map modal.

    Request body (JSON):
      {
        "name":      "<string>",
        "bank":      "BDO" | "BPI" | "MBK" | "LBP" | ... | "OTHER",
        "address":   "<optional string>",
        "latitude":  <float>,
        "longitude": <float>
      }
    """

    serializer_class   = ATMCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# GET /api/atms/tags/
# ---------------------------------------------------------------------------

class TagListView(generics.ListAPIView):
    """
    Returns the full list of available crowd-sourced tags.
    Used to populate the multi-select tag picker in the report modal.
    """

    queryset           = Tag.objects.all()
    serializer_class   = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
