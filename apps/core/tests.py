from django.test import TestCase, override_settings
from django.core import mail
from django.core.management import call_command
from django.conf import settings


class EmailConfigurationTests(TestCase):
    def test_lettermint_email_settings(self):
        """Verify Lettermint email settings are loaded correctly."""
        self.assertEqual(settings.EMAIL_HOST, "smtp.lettermint.co")
        self.assertEqual(settings.EMAIL_PORT, 587)
        self.assertTrue(settings.EMAIL_USE_TLS)
        self.assertEqual(settings.EMAIL_HOST_USER, "lettermint")
        self.assertIn("lm_", settings.EMAIL_HOST_PASSWORD)
        self.assertEqual(settings.LETTERMINT_API_KEY, settings.EMAIL_HOST_PASSWORD)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_test_email_management_command(self):
        """Test send_test_email management command places email in outbox."""
        call_command("send_test_email", "test@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])
        self.assertIn("Lettermint Email Test", mail.outbox[0].subject)
