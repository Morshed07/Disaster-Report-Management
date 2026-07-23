from rest_framework import status, generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HelpRequest
from .serializers import (
    HelpRequestConfirmationSerializer,
    HelpRequestCreateSerializer,
    HelpRequestSerializer,
)


class HelpRequestCreateAPIView(APIView):
    """
    POST /api/v1/help-requests/
    Accepts multipart/form-data so files can be uploaded alongside form fields.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = HelpRequestCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        help_request = serializer.save()

        confirmation = HelpRequestConfirmationSerializer(help_request)
        return Response(confirmation.data, status=status.HTTP_201_CREATED)


class HelpRequestListAPIView(generics.ListAPIView):
    """
    GET /api/v1/help-requests/
    List all submitted help requests.
    """

    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer


class HelpRequestDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/v1/help-requests/<request_number>/
    Retrieve details of a specific help request by request_number.
    """

    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer
    lookup_field = "request_number"
