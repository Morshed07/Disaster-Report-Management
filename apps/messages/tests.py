from unittest.mock import patch
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.messages.models import ContactMessage
from apps.messages.tasks import send_contact_message_email


class ContactMessageAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("contact-message-create")

    @patch("apps.messages.views.send_contact_message_email.delay")
    def test_submit_message_success(self, mock_email_task):
        """
        Ensure we can submit a new contact message and background task is queued.
        """
        data = {
            "name": "John Smith",
            "phone_number": "123456789",
            "email": "john.smith@example.com",
            "message": "Hi, I have a general question about disaster mitigation resources.",
            "privacy_policy_accepted": True,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], "John Smith")

        # Verify database record exists
        self.assertEqual(ContactMessage.objects.count(), 1)
        db_message = ContactMessage.objects.first()
        self.assertEqual(db_message.email, "john.smith@example.com")
        self.assertFalse(db_message.is_handled)

        # Verify background email task was dispatched
        mock_email_task.assert_called_once_with(db_message.id)

    def test_submit_message_privacy_validation_fails(self):
        """
        Ensure validation fails when privacy policy is not accepted.
        """
        data = {
            "name": "John Smith",
            "phone_number": "123456789",
            "email": "john.smith@example.com",
            "message": "Hello!",
            "privacy_policy_accepted": False,
        }

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("privacy_policy_accepted", response.data)


class ContactMessageTaskTests(TestCase):

    def setUp(self):
        self.contact_message = ContactMessage.objects.create(
            name="Jan de Vries",
            phone_number="0612345678",
            email="jan.devries@example.com",
            message="Ik wil graag meer informatie over de afhandeling van aardbevingsschade.",
            privacy_policy_accepted=True,
        )

    def test_send_contact_message_email_success(self):
        """
        Test that send_contact_message_email task sends confirmation to user and notification to admin.
        """
        mail.outbox.clear()

        result = send_contact_message_email(self.contact_message.id)
        self.assertTrue(result)

        # Expect 2 emails sent: 1 to user, 1 to admin
        self.assertEqual(len(mail.outbox), 2)

        # 1. User confirmation email
        user_msg = mail.outbox[0]
        self.assertEqual(user_msg.to, ["jan.devries@example.com"])
        self.assertEqual(user_msg.subject, "Bedankt voor uw bericht – Bevingshulp Noord")
        self.assertIn("Beste Jan,", user_msg.body)
        self.assertIn("Bedankt voor uw bericht via onze website. We hebben uw aanvraag in goede orde ontvangen.", user_msg.body)
        self.assertIn("Wat gebeurt er nu?", user_msg.body)
        self.assertIn("binnen één werkdag", user_msg.body)
        self.assertIn("050 211 1892", user_msg.body)
        self.assertIn("Team Bevingshulp Noord", user_msg.body)

        # Check HTML alternative
        self.assertTrue(len(user_msg.alternatives) > 0)
        html_content, mimetype = user_msg.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn("Beste Jan,", html_content)
        self.assertIn("Bedankt voor uw bericht via onze website", html_content)
        self.assertIn("Wat gebeurt er nu?", html_content)
        self.assertIn("binnen één werkdag", html_content)
        self.assertIn("050 211 1892", html_content)
        self.assertIn("Team Bevingshulp Noord", html_content)

        # 2. Admin notification email
        admin_msg = mail.outbox[1]
        self.assertEqual(admin_msg.to, ["info@bevingshulpnoord.nl"])
        self.assertIn("Jan de Vries", admin_msg.subject)
        self.assertIn("jan.devries@example.com", admin_msg.body)
        self.assertIn("0612345678", admin_msg.body)
        self.assertIn("Ik wil graag meer informatie over de afhandeling van aardbevingsschade.", admin_msg.body)

    def test_send_contact_message_email_not_found(self):
        """
        Test that task handles non-existent contact message ID gracefully.
        """
        mail.outbox.clear()
        result = send_contact_message_email(999999)
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
