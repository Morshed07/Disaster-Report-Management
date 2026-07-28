import shortuuid
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone


def generate_short_id() -> str:
    """Default primary key generator for all models in this app."""
    return shortuuid.uuid()


def generate_case_number() -> str:
    """
    Generates case numbers in the format shown on the confirmation /
    status pages, e.g. BN-2026-955463.
    Uses a numeric-only shortuuid alphabet so the suffix is all digits.
    """
    year = timezone.now().year
    su = shortuuid.ShortUUID(alphabet="0123456789")
    suffix = su.random(length=6)
    return f"BN-{year}-{suffix}"


class BuildingType(models.TextChoices):
    HOME = "home", "Home (Private home)"
    VVE = "vve", "Homeowners Association (Apartment / Homeowners Association)"
    RENTAL = "rental", "Rental property (Investment / rental)"
    COMMERCIAL = "commercial", "Commercial building (Commercial property)"
    # Legacy backward-compatibility choices
    RESIDENTIAL = "residential", "Residential / House (Woning)"
    INVESTMENT = "investment", "Investment / Rental property (Belegging / verhuur)"


class DamageScope(models.TextChoices):
    DAMAGE_INSIDE = "damage_inside", "Damage inside"
    DAMAGE_OUTSIDE = "damage_outside", "Damage outside"
    SUBSIDENCE = "subsidence", "Subsidence"


class ApplicableCase(models.TextChoices):
    NEW_REPORT = "new_report", "New damage report (Nieuwe schademelding)"
    RECORDING_BEFORE_RENOVATION = (
        "recording_before_renovation",
        "Recording before renovation",
    )
    SECOND_OPINION = "second_opinion", "Second opinion on ongoing file"
    OBJECTION_REVIEW = "objection_review", "Objection or review (Bezwaar of herziening)"
    OTHER = "other", "Other"


class ContactPreference(models.TextChoices):
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"
    BOTH = "both", "Both"


class CaseStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    UNDER_REVIEW = "under_review", "Under review"
    IN_PROGRESS = "in_progress", "In progress"
    APPROVED = "approved", "Approved"
    COMPLETED = "completed", "Completed"


class TimeStampedModel(models.Model):
    """Abstract base giving every model a shortuuid PK + timestamps."""

    id = models.CharField(
        primary_key=True,
        default=generate_short_id,
        editable=False,
        max_length=32,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DamageReport(TimeStampedModel):
    """
    Maps to the 3-step "Report earthquake damage" form (About you,
    About the property, Your situation) and resulting status page.
    """

    case_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_case_number,
        editable=False,
    )

    # ActiveCampaign CRM integration — stores the AC Deal ID so inbound
    # webhooks can reliably look up the matching DamageReport.
    activecampaign_deal_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="ActiveCampaign Deal ID for CRM sync.",
    )

    # --- Step 1: Contact & address fields ---
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, help_text="Street name and house number")
    city = models.CharField(max_length=100, blank=True, default="")
    postcode = models.CharField(max_length=10, blank=True, default="")

    # --- Step 2: About the property fields ---
    building_type = models.CharField(
        max_length=20,
        choices=BuildingType.choices,
        default=BuildingType.HOME,
    )
    damage_reported_before = models.BooleanField(
        default=False,
        help_text="Has damage been reported before?",
    )
    is_own_property = models.BooleanField(
        default=True,
        help_text="Is the property your property?",
    )

    # --- Step 3: Your situation fields ---
    damage_scope = models.JSONField(
        default=list,
        blank=True,
        help_text="List of damage aspects e.g. damage_inside, damage_outside, subsidence",
    )
    comments = models.TextField(
        blank=True,
        default="",
        help_text="Any additional information that is important to us.",
    )

    # --- Legacy / optional classification fields ---
    applicable_case = models.CharField(
        max_length=30,
        choices=ApplicableCase.choices,
        default=ApplicableCase.NEW_REPORT,
        blank=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Describe the damage in as much detail as possible.",
    )
    contact_preference = models.CharField(
        max_length=10,
        choices=ContactPreference.choices,
        default=ContactPreference.EMAIL,
        blank=True,
    )
    privacy_policy_accepted = models.BooleanField(default=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.case_number} — {self.name}"

    def save(self, *args, **kwargs):
        # Guarantee uniqueness of the human-friendly case number even
        # under (unlikely) collisions.
        if not self.case_number:
            self.case_number = generate_case_number()
        while (
            not self.pk
            and DamageReport.objects.filter(case_number=self.case_number).exists()
        ):
            self.case_number = generate_case_number()
        super().save(*args, **kwargs)


def damage_report_upload_path(instance: "DamageReportAttachment", filename: str) -> str:
    return f"damage_reports/{instance.damage_report.case_number}/{filename}"


class DamageReportAttachment(TimeStampedModel):
    """
    Optional photos / supporting documents uploaded with a damage report
    (drag-and-drop uploader in Image 5).
    """

    damage_report = models.ForeignKey(
        DamageReport,
        related_name="attachments",
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        upload_to=damage_report_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "pdf", "doc", "docx"]
            )
        ],
    )

    def __str__(self) -> str:
        return f"Attachment for {self.damage_report.case_number}"


class CaseUpdate(TimeStampedModel):
    """
    Maps to the "Updates" timeline entries and the "Progress of your
    application" steps shown on the case status page (Image 2).
    """

    damage_report = models.ForeignKey(
        DamageReport,
        related_name="updates",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20,
        choices=CaseStatus.choices,
        default=CaseStatus.RECEIVED,
        help_text="Status this update corresponds to on the progress timeline.",
    )
    note = models.TextField(
        help_text="Text shown to the applicant, e.g. "
        "'Your application has been reviewed and forwarded for further processing.'"
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Update for {self.damage_report.case_number} — {self.status}"