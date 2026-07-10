from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

from apps.reports.models import DamageReport, CaseStatus, BuildingType, ApplicableCase


class DamageReportAPITests(APITestCase):

    def setUp(self):
        self.create_url = reverse("report-list")
        self.check_status_url = reverse("report-check-status")

    @patch("apps.reports.tasks.send_confirmation_email.delay")
    def test_submit_damage_report_success(self, mock_email_task):
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
