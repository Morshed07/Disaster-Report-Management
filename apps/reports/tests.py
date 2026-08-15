from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from unittest.mock import patch, MagicMock

from apps.reports.models import DamageReport, CaseStatus, CaseUpdate, BuildingType, ApplicableCase


class DamageReportAPITests(APITestCase):

    def setUp(self):
        self.create_url = reverse("report-list")
        self.check_status_url = reverse("report-check-status")

    @patch("apps.reports.views._sync_damage_report_to_activecampaign")
    @patch("apps.reports.tasks.send_confirmation_email.delay")
    def test_submit_damage_report_success(self, mock_email_task, mock_ac_sync):
        """
        Ensure we can submit a new damage report with attachments.
        """
        # Create temporary mock files
        file1 = SimpleUploadedFile("photo1.jpg", b"file_content", content_type="image/jpeg")
        file2 = SimpleUploadedFile("doc1.pdf", b"pdf_content", content_type="application/pdf")

        data = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone_number": "1234567890",
            "address": "Kerklaan 12",
            "city": "Groningen",
            "postcode": "9700 AG",
            "building_type": BuildingType.RESIDENTIAL,
            "applicable_case": ApplicableCase.NEW_REPORT,
            "description": "This is a long description of the damage to satisfy the 20 character minimum.",
            "privacy_policy_accepted": True,
            "attachments": [file1, file2],
        }

        response = self.client.post(self.create_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("case_number", response.data)
        self.assertEqual(response.data["name"], "Jane Doe")
        self.assertEqual(response.data["status"], CaseStatus.RECEIVED)
        self.assertEqual(len(response.data["attachments"]), 2)
        self.assertEqual(response.data["attachments"][0]["filename"], "photo1.jpg")

        # Verify background email task was called with the generated case_number
        created_report = DamageReport.objects.get(name="Jane Doe")
        mock_email_task.assert_called_once_with(created_report.case_number)

        # Verify AC sync was called
        mock_ac_sync.assert_called_once_with(created_report)

    @patch("apps.reports.views._sync_damage_report_to_activecampaign")
    @patch("apps.reports.tasks.send_confirmation_email.delay")
    def test_submit_new_3step_damage_report_success(self, mock_email_task, mock_ac_sync):
        """
        Ensure we can submit a new 3-step damage report with step 1, step 2, step 3 fields.
        """
        data = {
            "name": "Jan Jansen",
            "email": "jan.jansen@example.nl",
            "phone_number": "0612345678",
            "address": "Extended Hereweg 12",
            "building_type": "home",
            "damage_reported_before": True,
            "is_own_property": True,
            "damage_scope": ["damage_inside", "subsidence"],
            "comments": "Cracks appeared on living room wall.",
        }

        response = self.client.post(self.create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("case_number", response.data)
        self.assertEqual(response.data["name"], "Jan Jansen")
        self.assertEqual(response.data["building_type"], "home")
        self.assertEqual(response.data["damage_reported_before"], True)
        self.assertEqual(response.data["is_own_property"], True)
        self.assertEqual(response.data["damage_scope"], ["damage_inside", "subsidence"])
        self.assertEqual(response.data["comments"], "Cracks appeared on living room wall.")

    def test_submit_damage_report_validation_fails(self):
        """
        Ensure validation errors are returned for description length and privacy policy.
        """
        data = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "address": "Kerklaan 12",
            "city": "Groningen",
            "postcode": "9700 AG",
            "description": "Too short",  # < 20 characters
            "privacy_policy_accepted": False,
        }

        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("description", response.data)
        self.assertIn("privacy_policy_accepted", response.data)

    def test_check_status_get_method(self):
        """
        Verify looking up status via GET request query parameters.
        """
        report = DamageReport.objects.create(
            name="Alice",
            email="alice@example.com",
            address="Street 1",
            city="Groningen",
            postcode="1234 AB",
            description="Alice's house got damaged in the recent minor earthquake.",
            privacy_policy_accepted=True,
        )

        response = self.client.get(
            self.check_status_url,
            {"case_number": report.case_number, "email": "alice@example.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["case_number"], report.case_number)
        self.assertEqual(response.data["status"], CaseStatus.RECEIVED)

    def test_check_status_post_method(self):
        """
        Verify looking up status via POST request body parameter.
        """
        report = DamageReport.objects.create(
            name="Bob",
            email="bob@example.com",
            address="Street 2",
            city="Groningen",
            postcode="1234 CD",
            description="Bob's roof had some shingles falling off due to tremors.",
            privacy_policy_accepted=True,
        )

        response = self.client.post(
            self.check_status_url,
            {"case_number": report.case_number, "email": "bob@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["case_number"], report.case_number)

    def test_check_status_not_found(self):
        """
        Verify appropriate 404 error is returned for invalid credentials.
        """
        response = self.client.post(
            self.check_status_url,
            {"case_number": "BN-2026-999999", "email": "nonexistent@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# ActiveCampaign Webhook Tests
# ---------------------------------------------------------------------------

@override_settings(ACTIVECAMPAIGN_WEBHOOK_SECRET="")
class ActiveCampaignWebhookTests(APITestCase):
    """Tests for the inbound ActiveCampaign webhook endpoint."""

    def setUp(self):
        self.webhook_url = reverse("activecampaign-webhook")
        self.report = DamageReport.objects.create(
            name="Charlie",
            email="charlie@example.com",
            address="Street 3",
            city="Groningen",
            postcode="1234 EF",
            description="Charlie's house needs state inspection for earthquake damage.",
            privacy_policy_accepted=True,
        )

    def test_phase2_stage_updates_status(self):
        """
        Phase 2 AC stage (State Inspection at Property) should create a
        CaseUpdate and map to IN_PROGRESS.
        """
        payload = {
            "type": "deal_pipeline_step_change",
            "deal[title]": f"Deal - {self.report.case_number}",
            "deal[contact_email]": "charlie@example.com",
            "deal[stage_title]": "State Inspection at Property",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["new_status"], CaseStatus.IN_PROGRESS)

        # Verify a CaseUpdate was created
        update = CaseUpdate.objects.filter(damage_report=self.report).first()
        self.assertIsNotNone(update)
        self.assertEqual(update.status, CaseStatus.IN_PROGRESS)

    def test_contract_signed_maps_to_received(self):
        """Stage 6 'Client / Contract Signed' → RECEIVED."""
        payload = {
            "deal[stage_title]": "Client / Contract Signed",
            "deal[contact_email]": "charlie@example.com",
        }
        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.data["new_status"], CaseStatus.RECEIVED)

    def test_earthquake_reported_maps_to_under_review(self):
        """Stage 7 'Earthquake Damage Reported' → UNDER_REVIEW."""
        payload = {
            "deal[stage_title]": "Earthquake Damage Reported",
            "deal[contact_email]": "charlie@example.com",
        }
        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.data["new_status"], CaseStatus.UNDER_REVIEW)

    def test_invoice_processed_maps_to_completed(self):
        """Stage 10 'Invoice Processed / Payout' → COMPLETED."""
        payload = {
            "deal[stage_title]": "Invoice Processed / Payout",
            "deal[contact_email]": "charlie@example.com",
        }
        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.data["new_status"], CaseStatus.COMPLETED)

    def test_phase1_stage_is_ignored(self):
        """
        Phase 1 stages (1–5) should be silently ignored — no CaseUpdate
        created, but always return 200.
        """
        payload = {
            "deal[stage_title]": "First Contact",
            "deal[contact_email]": "charlie@example.com",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ignored")

        # Verify NO CaseUpdate was created
        self.assertEqual(
            CaseUpdate.objects.filter(damage_report=self.report).count(), 0
        )

    def test_unknown_stage_is_ignored(self):
        """Unrecognised stage names should be ignored."""
        payload = {
            "deal[stage_title]": "Some Random Stage",
            "deal[contact_email]": "charlie@example.com",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ignored")

    def test_no_matching_report_returns_200_ignored(self):
        """Webhook for an unknown contact should return 200 with 'ignored'."""
        payload = {
            "deal[stage_title]": "State Inspection at Property",
            "deal[contact_email]": "nobody@example.com",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ignored")

    def test_lookup_by_deal_id(self):
        """Webhook should find the report via activecampaign_deal_id."""
        self.report.activecampaign_deal_id = "12345"
        self.report.save()

        payload = {
            "deal[id]": "12345",
            "deal[stage_title]": "Waiting for Report",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["new_status"], CaseStatus.IN_PROGRESS)
        self.assertEqual(response.data["case_number"], self.report.case_number)

    def test_lookup_by_case_number_in_title(self):
        """Webhook should extract case_number from deal title."""
        payload = {
            "deal[title]": f"{self.report.case_number} — Charlie",
            "deal[stage_title]": "Client / Contract Signed",
        }

        response = self.client.post(self.webhook_url, payload)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["case_number"], self.report.case_number)

    @override_settings(ACTIVECAMPAIGN_WEBHOOK_SECRET="my-secret-123")
    def test_webhook_secret_validation_rejects_bad_secret(self):
        """Webhook with wrong secret should get 403."""
        payload = {
            "deal[stage_title]": "State Inspection at Property",
            "deal[contact_email]": "charlie@example.com",
        }

        response = self.client.post(
            self.webhook_url + "?secret=wrong-secret", payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ACTIVECAMPAIGN_WEBHOOK_SECRET="my-secret-123")
    def test_webhook_secret_validation_accepts_correct_secret(self):
        """Webhook with correct secret should be processed."""
        payload = {
            "deal[stage_title]": "State Inspection at Property",
            "deal[contact_email]": "charlie@example.com",
        }

        response = self.client.post(
            self.webhook_url + "?secret=my-secret-123", payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")

    def test_stores_deal_id_on_first_webhook(self):
        """First webhook with deal[id] should store it on the DamageReport."""
        self.assertIsNone(self.report.activecampaign_deal_id)

        payload = {
            "deal[id]": "99999",
            "deal[contact_email]": "charlie@example.com",
            "deal[stage_title]": "Client / Contract Signed",
        }

        self.client.post(self.webhook_url, payload)
        self.report.refresh_from_db()
        self.assertEqual(self.report.activecampaign_deal_id, "99999")


# ---------------------------------------------------------------------------
# Outbound AC Sync Tests
# ---------------------------------------------------------------------------

class OutboundActiveCampaignSyncTests(APITestCase):
    """Tests for outbound sync when DamageReport is created."""

    def setUp(self):
        self.create_url = reverse("report-list")

    @patch("apps.reports.views.ActiveCampaignClient")
    @patch("apps.reports.tasks.send_confirmation_email.delay")
    def test_outbound_sync_calls_ac_client(self, mock_email, mock_ac_cls):
        """
        When a DamageReport is created, the AC client should be called
        to create a contact and deal.
        """
        mock_client = MagicMock()
        mock_client.create_or_update_contact.return_value = "contact-123"
        mock_client.create_deal.return_value = "deal-456"
        mock_ac_cls.return_value = mock_client

        data = {
            "name": "Jan De Vries",
            "email": "jan@example.com",
            "phone_number": "+31612345678",
            "address": "Kerklaan 12",
            "city": "Groningen",
            "postcode": "9700 AG",
            "building_type": BuildingType.RESIDENTIAL,
            "applicable_case": ApplicableCase.NEW_REPORT,
            "description": "Significant cracks appeared in the walls after the recent tremor.",
            "privacy_policy_accepted": True,
        }

        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert AC client was used
        mock_client.create_or_update_contact.assert_called_once_with(
            email="jan@example.com",
            first_name="Jan",
            last_name="De Vries",
            phone="+31612345678",
        )
        mock_client.create_deal.assert_called_once()

        # Verify deal_id was saved
        report = DamageReport.objects.get(email="jan@example.com")
        self.assertEqual(report.activecampaign_deal_id, "deal-456")

    @patch("apps.reports.views.ActiveCampaignClient")
    @patch("apps.reports.tasks.send_confirmation_email.delay")
    def test_ac_failure_does_not_block_response(self, mock_email, mock_ac_cls):
        """
        If ActiveCampaign fails, the user should still get their
        confirmation with a case number (non-blocking).
        """
        from apps.reports.integrations.activecampaign import ActiveCampaignError

        mock_client = MagicMock()
        mock_client.create_or_update_contact.side_effect = ActiveCampaignError("API down")
        mock_ac_cls.return_value = mock_client

        data = {
            "name": "Anna Jansen",
            "email": "anna@example.com",
            "address": "Oosterstraat 5",
            "city": "Groningen",
            "postcode": "9700 AB",
            "description": "Water damage in the basement from foundation crack after earthquake.",
            "privacy_policy_accepted": True,
        }

        response = self.client.post(self.create_url, data, format="json")
        # User should still get 201 with case_number even though AC failed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("case_number", response.data)

    def test_send_confirmation_email_sends_user_and_admin_emails(self):
        """
        Verify send_confirmation_email sends a confirmation to the user
        and a lead alert email to admin (info@bevingshulpnoord.nl).
        """
        from django.core import mail
        from apps.reports.tasks import send_confirmation_email

        report = DamageReport.objects.create(
            name="Test Lead User",
            email="leaduser@example.com",
            phone_number="0612345678",
            address="Grote Markt 1",
            city="Groningen",
            postcode="9711 LV",
            description="Test damage report description for verification.",
            privacy_policy_accepted=True,
        )

        result = send_confirmation_email(report.case_number)
        self.assertTrue(result)

        # 2 emails should be sent: 1 to user, 1 to admin
        self.assertEqual(len(mail.outbox), 2)
        recipients = [msg.to[0] for msg in mail.outbox]
        self.assertIn("leaduser@example.com", recipients)
        self.assertIn("info@bevingshulpnoord.nl", recipients)

        # Check admin message subject
        admin_msg = next(msg for msg in mail.outbox if "info@bevingshulpnoord.nl" in msg.to)
        self.assertIn("New Lead", admin_msg.subject)
        self.assertIn(report.case_number, admin_msg.body)
        self.assertIn("Test Lead User", admin_msg.body)
