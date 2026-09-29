"""
ATM Social Map — DRF API Views
================================
API endpoints powering the ATM Social Map:
  - ATMListView: GET /api/atms/ (GeoJSON FeatureCollection)
  - ATMNearbyView: GET /api/atms/nearby/?lat=&lng=&radius=
  - StatusReportView: POST /api/atms/report/ (Operational status updates)
  - ATMReportCreateView: POST /api/atms/issues/ (Crowd discrepancy/issue reports)
  - ATMAddView: POST /api/atms/add/ (Add new ATM pin)
  - BankListView: GET /api/atms/banks/ (Available banks)
  - CardNetworkListView: GET /api/atms/networks/ (Available card networks)
"""

import math
from django.db.models import Prefetch
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ATM, ATMReport, Bank, CardNetwork, StatusReport
from .serializers import (
    ATMCreateSerializer,
    ATMGeoSerializer,
    ATMReportSerializer,
    BankSerializer,
    CardNetworkSerializer,
    StatusReportSerializer,
)


def _atm_queryset_with_latest_report():
    return (
        ATM.objects
        .select_related('bank')
        .prefetch_related(
            'networks',
            Prefetch(
                'status_reports',
                queryset=StatusReport.objects
                         .order_by('-created_at')
                         .select_related('user'),
                to_attr='_prefetched_reports',
            )
        )
    )


def _attach_latest_report(atm_list):
    for atm in atm_list:
        reports = getattr(atm, '_prefetched_reports', [])
        atm._latest_report = reports[0] if reports else None
    return atm_list


def _haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lon coordinates."""
    r = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


class ATMListView(APIView):
    """Returns all ATMs as a GeoJSON FeatureCollection."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        atms = list(_atm_queryset_with_latest_report())
        _attach_latest_report(atms)
        serializer = ATMGeoSerializer(atms, many=True, context={'request': request})
        return Response(serializer.data)


class ATMNearbyView(APIView):
    """Returns ATMs within `radius` metres of (lat, lng), ordered by distance."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            lat = float(request.query_params['lat'])
            lng = float(request.query_params['lng'])
        except (KeyError, ValueError, TypeError):
            return Response(
                {'error': 'Query parameters `lat` and `lng` are required and must be numeric.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            radius = float(request.query_params.get('radius', 3000))
        except (ValueError, TypeError):
            radius = 3000.0

        all_atms = list(_atm_queryset_with_latest_report())
        _attach_latest_report(all_atms)

        nearby_atms = []
        for atm in all_atms:
            if atm.latitude is not None and atm.longitude is not None:
                dist = _haversine(lat, lng, float(atm.latitude), float(atm.longitude))
                if dist <= radius:
                    nearby_atms.append((dist, atm))

        nearby_atms.sort(key=lambda x: x[0])
        sorted_atms = [item[1] for item in nearby_atms]

        serializer = ATMGeoSerializer(sorted_atms, many=True, context={'request': request})
        return Response(serializer.data)


class StatusReportView(generics.CreateAPIView):
    """Authenticated users submit a crowd operational status report."""
    serializer_class = StatusReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ATMReportCreateView(generics.CreateAPIView):
    """Authenticated users submit fee discrepancies, inaccurate locations, or general notes."""
    serializer_class = ATMReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ATMAddView(generics.CreateAPIView):
    """Authenticated users add a new ATM pin."""
    serializer_class = ATMCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class BankListView(generics.ListAPIView):
    """List all banks for dropdowns/filters."""
    queryset = Bank.objects.all()
    serializer_class = BankSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CardNetworkListView(generics.ListAPIView):
    """List all card networks."""
    queryset = CardNetwork.objects.all()
    serializer_class = CardNetworkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
