from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DamageReport
from .serializers import (
    CaseStatusLookupSerializer,
    ContactMessageSerializer,
    DamageReportConfirmationSerializer,
    DamageReportCreateSerializer,
    DamageReportStatusSerializer,
)
from .models import SubsidyScanRequest
from .serializers import (
    SubsidyScanRequestConfirmationSerializer,
    SubsidyScanRequestSerializer,
)


# ---------------------------------------------------------------------------
# Image 1 — "Send us a message" contact form
# ---------------------------------------------------------------------------
class ContactMessageAPIView(APIView):
    """
    POST /api/v1/contact/
    """

    def post(self, request, *args, **kwargs):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Image 5 — "Report damage" form  /  Image 4 — confirmation screen
# ---------------------------------------------------------------------------
class DamageReportCreateAPIView(APIView):
    """
    POST /api/v1/reports/

    Accepts multipart/form-data so files can be uploaded alongside the
    form fields ("attachments" as one or more files).
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = DamageReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        damage_report = serializer.save()

        confirmation = DamageReportConfirmationSerializer(damage_report)
        return Response(confirmation.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Image 3 — "Check case status" form  /  Image 2 — "Case status" page
# ---------------------------------------------------------------------------
class CaseStatusCheckAPIView(APIView):
    """
    GET /api/v1/reports/check-status/?case_number=BN-2026-955463&email=you@example.com
    """

    def get(self, request, *args, **kwargs):
        lookup_serializer = CaseStatusLookupSerializer(data=request.query_params)
        lookup_serializer.is_valid(raise_exception=True)
        damage_report: DamageReport = lookup_serializer.validated_data["damage_report"]

        status_serializer = DamageReportStatusSerializer(damage_report)
        return Response(status_serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Subsidy scan form — "Discover in 2 minutes which subsidies are
# available to you"
# ---------------------------------------------------------------------------
class SubsidyScanRequestAPIView(APIView):
    """
    POST /api/v1/subsidy-scan/
    """

    def post(self, request, *args, **kwargs):
        serializer = SubsidyScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subsidy_scan_request: SubsidyScanRequest = serializer.save()

        confirmation = SubsidyScanRequestConfirmationSerializer(subsidy_scan_request)
        return Response(confirmation.data, status=status.HTTP_201_CREATED)
