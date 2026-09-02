import os
import logging
from email.mime.image import MIMEImage
from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import ContactMessage

logger = logging.getLogger(__name__)


@shared_task(name="apps.messages.tasks.send_contact_message_email")
def send_contact_message_email(message_id: int) -> bool:
    """
    Sends a confirmation email to the user when their contact message is received,
    and sends a notification email to the admin team.
    """
    try:
        contact_message = ContactMessage.objects.get(pk=message_id)
    except ContactMessage.DoesNotExist:
        logger.error(f"Cannot send contact confirmation email. ContactMessage {message_id} not found.")
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Bevingshulp Noord <info@bevingshulpnoord.nl>")
    admin_email = getattr(settings, "ADMIN_EMAIL", "info@bevingshulpnoord.nl")

    # -----------------------------------------------------------------------
    # 1. User Confirmation Email
    # -----------------------------------------------------------------------
    parts = contact_message.name.strip().split()
    voornaam = parts[0] if parts else contact_message.name

    user_subject = "Bedankt voor uw bericht – Bevingshulp Noord"
    user_context = {
        "voornaam": voornaam,
        "contact_message": contact_message,
    }

    user_html_message = render_to_string(
        "messages/emails/contact_message_confirmation.html",
        user_context,
    )

    user_message = (
        f"Beste {voornaam},\n\n"
        f"Bedankt voor uw bericht via onze website. We hebben uw aanvraag in goede orde ontvangen.\n\n"
        f"Wat gebeurt er nu?\n"
        f"Een van onze specialisten bekijkt uw bericht en neemt binnen één werkdag persoonlijk contact met u op. "
        f"We bespreken uw situatie en kijken samen hoe we u het beste kunnen helpen.\n\n"
        f"Heeft u in de tussentijd aanvullende informatie, documenten of foto's die voor uw situatie van belang kunnen zijn? "
        f"Dan kunt u deze gerust per e-mail naar ons toesturen.\n\n"
        f"Wilt u liever direct even overleggen? Neem dan gerust telefonisch contact met ons op via 050 211 1892.\n\n"
        f"Met vriendelijke groet,\n\n"
        f"Team Bevingshulp Noord\n\n"
        f"---\n"
        f"Bevingshulp Noord\n"
        f"Advies | Subsidies | Herstel\n"
        f"Telefoon: 050 211 1892\n"
        f"E-mail: info@bevingshulpnoord.nl\n"
        f"Website: www.bevingshulpnoord.nl\n"
        f"Adres: Blekerstraat 28A – 9718 EC Groningen"
    )

    user_email_sent = False
    try:
        email_msg = EmailMultiAlternatives(
            subject=user_subject,
            body=user_message,
            from_email=from_email,
            to=[contact_message.email],
        )
        email_msg.attach_alternative(user_html_message, "text/html")

        # Attach logo as inline MIMEImage (CID) so email clients display it reliably
        icon_candidates = [
            os.path.join(settings.BASE_DIR, "static", "icon", "icon.png"),
            os.path.join(str(getattr(settings, "STATIC_ROOT", "")), "icon", "icon.png"),
            os.path.join(settings.BASE_DIR, "staticfiles", "icon", "icon.png"),
        ]
        for icon_path in icon_candidates:
            if icon_path and os.path.exists(icon_path):
                try:
                    with open(icon_path, "rb") as f:
                        img = MIMEImage(f.read())
                        img.add_header("Content-ID", "<logo_icon>")
                        img.add_header("Content-Disposition", "inline", filename="icon.png")
                        email_msg.attach(img)
                    break
                except Exception as img_err:
                    logger.warning(f"Could not attach inline logo_icon: {img_err}")

        email_msg.send(fail_silently=False)
        user_email_sent = True
        logger.info(f"Confirmation email successfully sent for ContactMessage {message_id} to user {contact_message.email}")
    except Exception as e:
        logger.error(f"Failed to send user confirmation email for ContactMessage {message_id}: {e}")

    # -----------------------------------------------------------------------
    # 2. Admin Notification Email
    # -----------------------------------------------------------------------
    admin_subject = f"🚨 Nieuw contactbericht ontvangen - {contact_message.name}"
    admin_message = (
        f"Nieuw contactbericht ontvangen via het contactformulier!\n\n"
        f"--- BERICHT DETAILS ---\n"
        f"Naam / Name: {contact_message.name}\n"
        f"E-mail: {contact_message.email}\n"
        f"Telefoon / Phone: {contact_message.phone_number or 'N/A'}\n"
        f"Datum / Date: {contact_message.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(contact_message, 'created_at') and contact_message.created_at else 'N/A'}\n\n"
        f"--- BERICHT / MESSAGE ---\n"
        f"{contact_message.message}\n\n"
        f"Bekijk het bericht in het Django Admin panel."
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
        logger.info(f"Admin notification email sent for ContactMessage {message_id} to {admin_email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification email for ContactMessage {message_id}: {e}")

    return user_email_sent or admin_email_sent
