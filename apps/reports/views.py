import logging
import re

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .integrations.activecampaign import ActiveCampaignClient, ActiveCampaignError
from .models import CaseStatus, CaseUpdate, DamageReport
from .serializers import DamageReportCreateSerializer, DamageReportSerializer
from .tasks import send_confirmation_email

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outbound helper — called after form submission to sync to AC
# ---------------------------------------------------------------------------

def _sync_damage_report_to_activecampaign(report: DamageReport) -> None:
    """
    Push a newly-created DamageReport to ActiveCampaign as a Contact + Deal.

    Wrapped in try/except so failures are logged but never block the
    user's form submission response.
    """
    try:
        client = ActiveCampaignClient()

        # Split name into first/last for AC's contact model
        parts = report.name.strip().split(maxsplit=1)
        first_name = parts[0] if parts else report.name
        last_name = parts[1] if len(parts) > 1 else ""

        contact_id = client.create_or_update_contact(
            email=report.email,
            first_name=first_name,
            last_name=last_name,
            phone=report.phone_number,
        )

        if contact_id:
            deal_id = client.create_deal(
                title=f"{report.case_number} — {report.name}",
                contact_id=contact_id,
                pipeline_id=settings.ACTIVECAMPAIGN_SCHADECHECK_PIPELINE_ID,
                stage_id=settings.ACTIVECAMPAIGN_NEW_LEADS_STAGE_ID,
                case_number=report.case_number,
            )
            if deal_id:
                report.activecampaign_deal_id = deal_id
                report.save(update_fields=["activecampaign_deal_id"])

    except ActiveCampaignError:
        logger.exception(
            "ActiveCampaign sync failed for DamageReport %s — continuing.",
            report.case_number,
        )
    except Exception:
        logger.exception(
            "Unexpected error during AC sync for %s — continuing.",
            report.case_number,
        )


# ---------------------------------------------------------------------------
# DamageReport CRUD ViewSet
# ---------------------------------------------------------------------------

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

        # Outbound sync → ActiveCampaign (non-blocking)
        _sync_damage_report_to_activecampaign(instance)

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


# ---------------------------------------------------------------------------
# ActiveCampaign Webhook endpoint — inbound deal stage sync
# ---------------------------------------------------------------------------

# AC pipeline stages 6–10 (Phase 2) mapped to our website CaseStatus.
# Phase 1 stages (1–5) are internal CRM stages and should be ignored.
AC_STAGE_TO_CASE_STATUS = {
    "client / contract signed": CaseStatus.RECEIVED,
    "contract signed": CaseStatus.RECEIVED,
    "earthquake damage reported": CaseStatus.UNDER_REVIEW,
    "damage reported": CaseStatus.UNDER_REVIEW,
    "state inspection at property": CaseStatus.IN_PROGRESS,
    "state inspection": CaseStatus.IN_PROGRESS,
    "waiting for report": CaseStatus.IN_PROGRESS,
    "invoice processed / payout": CaseStatus.COMPLETED,
    "invoice processed": CaseStatus.COMPLETED,
    "payout": CaseStatus.COMPLETED,
}

# Phase 1 stage names — these are explicitly ignored (no-op).
AC_PHASE1_STAGES = {
    "new lead",
    "new leads",
    "first contact",
    "no contact",
    "no contact (second attempt)",
    "inspection appointment scheduled",
    "inspection scheduled",
    "disqualified",
}


class ActiveCampaignWebhookAPIView(APIView):
    """
    POST /api/v1/webhooks/activecampaign/

    Receives deal & stage updates from ActiveCampaign webhooks and syncs
    the corresponding DamageReport case status timeline.

    Only Phase 2 stages (6–10) update our site.  Phase 1 (1–5) and
    unrecognised stages are silently ignored with a 200 response (AC
    expects a fast 200 and never retries).
    """

    parser_classes = [FormParser, JSONParser, MultiPartParser]

    def post(self, request, *args, **kwargs):
        # ----- Optional shared-secret verification -----
        webhook_secret = getattr(settings, "ACTIVECAMPAIGN_WEBHOOK_SECRET", "")
        if webhook_secret:
            provided = request.query_params.get("secret", "")
            if provided != webhook_secret:
                return Response(
                    {"status": "error", "message": "Invalid webhook secret."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        data = request.data

        # 1. Extract stage title/name from the webhook payload
        raw_stage = (
            data.get("deal[stage_title]")
            or data.get("deal[stage]")
            or data.get("stage_title")
            or data.get("stage")
            or data.get("deal[stage_name]")
            or ""
        )
        stage_key = str(raw_stage).strip().lower()

        # 2. Ignore Phase 1 stages or unrecognised stages
        if stage_key in AC_PHASE1_STAGES:
            return Response(
                {"status": "ignored", "message": f"Phase 1 stage '{raw_stage}' — no action taken."},
                status=status.HTTP_200_OK,
            )

        new_status = AC_STAGE_TO_CASE_STATUS.get(stage_key)
        if not new_status:
            return Response(
                {"status": "ignored", "message": f"Unrecognised stage '{raw_stage}' — no action taken."},
                status=status.HTTP_200_OK,
            )

        # 3. Identify the DamageReport
        deal_id = (
            data.get("deal[id]")
            or data.get("deal_id")
            or ""
        )
        case_number = (
            data.get("case_number")
            or data.get("deal[custom_fields][case_number]")
            or ""
        )
        email = (
            data.get("email")
            or data.get("deal[contact_email]")
            or data.get("contact[email]")
            or data.get("contact_email")
            or ""
        )
        deal_title = data.get("deal[title]") or data.get("title") or ""

        # Try to extract case_number from the deal title (e.g. "BN-2026-123456 — Jan")
        if not case_number and deal_title:
            match = re.search(r"BN-\d{4}-\d{6}", str(deal_title))
            if match:
                case_number = match.group(0)

        # Lookup priority: deal_id → case_number → email
        report = None
        if deal_id:
            report = DamageReport.objects.filter(
                activecampaign_deal_id=deal_id
            ).first()

        if not report and case_number:
            report = DamageReport.objects.filter(
                case_number=case_number
            ).first()

        if not report and email:
            report = DamageReport.objects.filter(email__iexact=email).first()

        if not report:
            return Response(
                {
                    "status": "ignored",
                    "message": "No matching damage report found.",
                },
                status=status.HTTP_200_OK,
            )

        # 4. Create CaseUpdate timeline entry
        status_display = dict(CaseStatus.choices).get(new_status, new_status)
        note = f"Status updated to '{status_display}' via ActiveCampaign CRM."
        if raw_stage:
            note += f" (Stage: {raw_stage})"

        case_update = CaseUpdate.objects.create(
            damage_report=report,
            status=new_status,
            note=note,
        )

        # Store deal_id if we didn't have it yet
        if deal_id and not report.activecampaign_deal_id:
            report.activecampaign_deal_id = deal_id
            report.save(update_fields=["activecampaign_deal_id"])

        return Response(
            {
                "status": "success",
                "case_number": report.case_number,
                "new_status": new_status,
                "update_id": case_update.id,
            },
            status=status.HTTP_200_OK,
        )
