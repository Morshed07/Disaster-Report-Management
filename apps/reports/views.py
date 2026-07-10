from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DamageReport
from .serializers import DamageReportSerializer, DamageReportCreateSerializer
from .tasks import send_confirmation_email


class DamageReportViewSet(viewsets.ModelViewSet):
    queryset = DamageReport.objects.all()
    lookup_field = "case_number"

    def get_serializer_class(self):
        if self.action == "create":
            return DamageReportCreateSerializer
        return DamageReportSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Trigger background Celery confirmation task
        send_confirmation_email.delay(instance.case_number)

        # Return full detail read serializer format
        read_serializer = DamageReportSerializer(
            instance, context={"request": request}
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            read_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False, methods=["get", "post"], url_path="check-status")
    def check_status(self, request):
        """
        API endpoint to retrieve the status of an application.
        Accepts case_number and email in body (POST) or query params (GET).
        """
        # Read from POST data or GET query parameters
        data = request.data if request.method == "POST" else request.query_params
        case_number = data.get("case_number", "").strip()
        email = data.get("email", "").strip()

        if not case_number or not email:
            return Response(
                {"error": "Both 'case_number' and 'email' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Case-insensitive email search to be user-friendly
            report = DamageReport.objects.get(
                case_number=case_number, email__iexact=email
            )
        except DamageReport.DoesNotExist:
            return Response(
                {
                    "error": "No matching damage report found with the provided case number and email."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DamageReportSerializer(report, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
