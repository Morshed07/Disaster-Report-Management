import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import DamageReport

logger = logging.getLogger(__name__)


@shared_task(name="apps.reports.tasks.send_confirmation_email")
def send_confirmation_email(case_number: str) -> bool:
    """
    Sends a confirmation email to the user when their damage report is received.
    """
    try:
        report = DamageReport.objects.get(case_number=case_number)
    except DamageReport.DoesNotExist:
        logger.error(f"Cannot send confirmation email. Case {case_number} not found.")
        return False

    subject = f"Damage Report Submitted - {report.case_number}"
    message = (
        f"Dear {report.name},\n\n"
        f"Thank you for submitting your damage report.\n\n"
        f"We have received your application and created a case for you.\n"
        f"Your Case Number is: {report.case_number}\n\n"
        f"You can use this number along with your email address ({report.email}) "
        f"to track the progress of your application on our status portal.\n\n"
        f"Best regards,\n"
        f"Disaster Management Team"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@disaster.gov")
    recipient_list = [report.email]

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Confirmation email successfully sent for case {case_number} to {report.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email for case {case_number}: {e}")
        return False
