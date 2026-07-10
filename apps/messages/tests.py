from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.messages.models import ContactMessage


class ContactMessageAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("contact-message-create")

    def test_submit_message_success(self):
        """
        Ensure we can submit a new contact message.
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
