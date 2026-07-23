import shortuuid
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone

from apps.reports.models import TimeStampedModel


def generate_request_number() -> str:
    """
    Generates human-readable request numbers in the format HR-2026-955463.
    Uses numeric-only shortuuid alphabet for suffix digits.
    """
    year = timezone.now().year
    su = shortuuid.ShortUUID(alphabet="0123456789")
    suffix = su.random(length=6)
    return f"HR-{year}-{suffix}"


class HelpType(models.TextChoices):
    CLAIMS_HANDLING = "claims_handling", "Claims handling"
    PRE_SHOT = "pre_shot", "Pre shot"
    SECOND_OPINION = "second_opinion", "Second opinion"
    OBJECTION_PROCEDURES = "objection_procedures", "Objection procedures"
    REPAIR_OWN_CONTRACTOR = "repair_own_contractor", "Repair own contractor"
    OTHERWISE = "otherwise", "Otherwise"


class ContactPreference(models.TextChoices):
    EMAIL = "email", "E-mail"
    PHONE = "phone", "Telephone"
    BOTH = "both", "Both"


class HelpRequest(TimeStampedModel):
    """
    Maps to the "Request help" form.
    """

    request_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_request_number,
        editable=False,
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.CharField(
        max_length=255, help_text="Street name and house number"
    )
    help_type = models.CharField(
        max_length=30,
        choices=HelpType.choices,
        default=HelpType.SECOND_OPINION,
    )
    description = models.TextField(
        help_text="Describe your situation in as much detail as possible: when did it start, what does it look like, and are there any safety risks?"
    )
    contact_preference = models.CharField(
        max_length=10,
        choices=ContactPreference.choices,
        default=ContactPreference.EMAIL,
    )
    privacy_policy_accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Help request"
        verbose_name_plural = "Help requests"

    def __str__(self) -> str:
        return f"{self.request_number} — {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = generate_request_number()
        while (
            not self.pk
            and HelpRequest.objects.filter(request_number=self.request_number).exists()
        ):
            self.request_number = generate_request_number()
        super().save(*args, **kwargs)


def help_request_upload_path(instance: "HelpRequestAttachment", filename: str) -> str:
    return f"help_requests/{instance.help_request.request_number}/{filename}"


class HelpRequestAttachment(TimeStampedModel):
    """
    Optional photos / supporting documents uploaded with a help request.
    """

    help_request = models.ForeignKey(
        HelpRequest,
        related_name="attachments",
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        upload_to=help_request_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "pdf", "doc", "docx"]
            )
        ],
    )

    def __str__(self) -> str:
        return f"Attachment for {self.help_request.request_number}"
