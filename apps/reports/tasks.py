import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import DamageReport

logger = logging.getLogger(__name__)


@shared_task(name="apps.reports.tasks.send_confirmation_email")
def send_confirmation_email(case_number: str) -> bool:
    """
    Sends a confirmation email to the user when their damage report is received,
    and sends a lead notification email to the admin team (info@bevingshulpnoord.nl).
    """
    try:
        report = DamageReport.objects.get(case_number=case_number)
    except DamageReport.DoesNotExist:
        logger.error(f"Cannot send confirmation email. Case {case_number} not found.")
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "info@bevingshulpnoord.nl")
    admin_email = getattr(settings, "ADMIN_EMAIL", "info@bevingshulpnoord.nl")

    # -----------------------------------------------------------------------
    # 1. User Confirmation Email
    # -----------------------------------------------------------------------
    user_subject = f"Damage Report Submitted - {report.case_number}"
    user_message = (
        f"Dear {report.name},\n\n"
        f"Thank you for submitting your damage report.\n\n"
        f"We have received your application and created a case for you.\n"
        f"Your Case Number is: {report.case_number}\n\n"
        f"You can use this number along with your email address ({report.email}) "
        f"to track the progress of your application on our status portal.\n\n"
        f"Best regards,\n"
        f"Disaster Management Team"
    )

    user_email_sent = False
    try:
        send_mail(
            subject=user_subject,
            message=user_message,
            from_email=from_email,
            recipient_list=[report.email],
            fail_silently=False,
        )
        user_email_sent = True
        logger.info(f"Confirmation email successfully sent for case {case_number} to user {report.email}")
    except Exception as e:
        logger.error(f"Failed to send user confirmation email for case {case_number}: {e}")

    # -----------------------------------------------------------------------
    # 2. Admin Lead Notification Email
    # -----------------------------------------------------------------------
    addr_str = getattr(report, "address", "") or f"{getattr(report, 'street_name', '')} {getattr(report, 'house_number', '')}".strip()
    city_str = getattr(report, "city", "") or getattr(report, "place", "") or "N/A"
    postcode_str = getattr(report, "postcode", "") or getattr(report, "postal_code", "") or "N/A"
    damage_scope_val = getattr(report, "damage_scope", None)
    if isinstance(damage_scope_val, list):
        damage_scope_str = ", ".join(map(str, damage_scope_val))
    else:
        damage_scope_str = str(damage_scope_val) if damage_scope_val else "N/A"

    latest_update = report.updates.order_by("-created_at").first()
    status_val = latest_update.status if latest_update else "received"

    admin_subject = f"🚨 New Lead / Damage Report Generated - {report.case_number}"
    admin_message = (
        f"Nieuwe schademelding ontvangen! / New Lead Generated!\n\n"
        f"--- LEAD DETAILS ---\n"
        f"Dossiernummer / Case Number: {report.case_number}\n"
        f"Naam / Name: {report.name}\n"
        f"E-mail: {report.email}\n"
        f"Telefoon / Phone: {report.phone_number or 'N/A'}\n"
        f"Adres / Address: {addr_str or 'N/A'}\n"
        f"Postcode: {postcode_str}\n"
        f"Plaats / City: {city_str}\n"
        f"Gebouwtype / Building Type: {getattr(report, 'building_type', 'N/A')}\n"
        f"Eerder gemeld / Reported before: {'Ja' if getattr(report, 'damage_reported_before', False) else 'Nee'}\n"
        f"Eigen pand / Own property: {'Ja' if getattr(report, 'is_own_property', False) else 'Nee'}\n"
        f"Omvang schade / Damage scope: {damage_scope_str}\n"
        f"Status: {status_val}\n\n"
        f"--- OPMERKINGEN / DESCRIPTION ---\n"
        f"{getattr(report, 'comments', '') or getattr(report, 'description', '') or 'Geen opmerkingen'}\n\n"
        f"Bekijk het dossier in het Django Admin panel of ActiveCampaign."
    )

    admin_email_sent = False
    try:
        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=from_email,
            recipient_list=[admin_email],
            fail_silently=False,
        )
        admin_email_sent = True
        logger.info(f"Admin notification email sent for case {case_number} to {admin_email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification email for case {case_number}: {e}")

    return user_email_sent or admin_email_sent
