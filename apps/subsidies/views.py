import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SubsidyScanRequest
from .serializers import (
    SubsidyScanRequestConfirmationSerializer,
    SubsidyScanRequestSerializer,
)
from apps.reports.integrations.activecampaign import (
    ActiveCampaignClient,
    ActiveCampaignError,
)

logger = logging.getLogger(__name__)


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

        # Outbound sync → ActiveCampaign (non-blocking)
        self._sync_to_activecampaign(subsidy_scan_request)

        # Send notification email to admin (non-blocking)
        self._send_admin_email_notification(subsidy_scan_request)

        confirmation = SubsidyScanRequestConfirmationSerializer(subsidy_scan_request)
        return Response(confirmation.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _send_admin_email_notification(scan: SubsidyScanRequest) -> None:
        """
        Send notification email to admin when a new SubsidyScanRequest is created.
        """
        try:
            from django.core.mail import send_mail
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "info@bevingshulpnoord.nl")
            admin_email = getattr(settings, "ADMIN_EMAIL", "info@bevingshulpnoord.nl")

            subject = f"🚨 New Subsidy Scan Lead - {scan.full_name}"
            message = (
                f"Nieuwe Subsidiescan aanvraag ontvangen! / New Subsidy Scan Lead!\n\n"
                f"Naam / Name: {scan.full_name}\n"
                f"E-mail: {scan.email}\n"
                f"Telefoon / Phone: {getattr(scan, 'phone_number', '') or 'N/A'}\n"
                f"Postcode: {getattr(scan, 'postcode', '') or getattr(scan, 'postal_code', '') or 'N/A'}\n"
                f"Huisnummer / House Number: {getattr(scan, 'house_number', '') or 'N/A'}\n\n"
                f"Bekijk de aanvraag in het Django Admin panel of ActiveCampaign."
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[admin_email],
                fail_silently=True,
            )
            logger.info(f"Admin email notification sent for SubsidyScanRequest {scan.pk} to {admin_email}")
        except Exception as e:
            logger.error(f"Failed to send admin email for SubsidyScanRequest {scan.pk}: {e}")

    @staticmethod
    def _sync_to_activecampaign(scan: SubsidyScanRequest) -> None:
        """
        Push a newly-created SubsidyScanRequest to ActiveCampaign.
        Failures are logged but never block the user response.
        """
        try:
            client = ActiveCampaignClient()

            parts = scan.full_name.strip().split(maxsplit=1)
            first_name = parts[0] if parts else scan.full_name
            last_name = parts[1] if len(parts) > 1 else ""

            contact_id = client.create_or_update_contact(
                email=scan.email,
                first_name=first_name,
                last_name=last_name,
                phone=scan.phone_number,
            )

            if contact_id:
                stage_id = getattr(settings, "ACTIVECAMPAIGN_SUBSIDIESCAN_NEW_LEADS_STAGE_ID", "") or settings.ACTIVECAMPAIGN_NEW_LEADS_STAGE_ID
                client.create_deal(
                    title=f"Subsidiescan — {scan.full_name}",
                    contact_id=contact_id,
                    pipeline_id=settings.ACTIVECAMPAIGN_SUBSIDIESCAN_PIPELINE_ID,
                    stage_id=stage_id,
                )

        except ActiveCampaignError:
            logger.exception(
                "ActiveCampaign sync failed for SubsidyScanRequest %s — continuing.",
                scan.pk,
            )
        except Exception:
            logger.exception(
                "Unexpected error during AC sync for SubsidyScanRequest %s — continuing.",
                scan.pk,
            )
