from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SubsidyScanRequest
from .serializers import (
    SubsidyScanRequestConfirmationSerializer,
    SubsidyScanRequestSerializer,
)


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

