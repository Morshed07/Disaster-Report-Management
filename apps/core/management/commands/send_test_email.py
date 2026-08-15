from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Sends a test email via configured email backend (Lettermint SMTP)"

    def add_arguments(self, parser):
        parser.add_argument(
            "recipient",
            type=str,
            help="Email address of the recipient to send the test email to",
        )

    def handle(self, *args, **options):
        recipient = options["recipient"]
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Bevingshulp Noord <info@bevingshulpnoord.nl>")

        self.stdout.write(f"Sending test email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
        self.stdout.write(f"From: {from_email}")
        self.stdout.write(f"To: {recipient}")

        try:
            sent_count = send_mail(
                subject="Lettermint Email Test - Bevingshulp Noord",
                message=(
                    "Hello,\n\n"
                    "This is a test email from Bevingshulp Noord system verifying "
                    "that Lettermint SMTP integration is working correctly.\n\n"
                    "Best regards,\n"
                    "Bevingshulp Noord Team"
                ),
                from_email=from_email,
                recipient_list=[recipient],
                fail_silently=False,
            )
            if sent_count > 0:
                self.stdout.write(self.style.SUCCESS(f"Successfully sent test email to {recipient}!"))
            else:
                self.stdout.write(self.style.WARNING("send_mail returned 0 sent messages."))
        except Exception as e:
            raise CommandError(f"Failed to send email via Lettermint: {e}")
