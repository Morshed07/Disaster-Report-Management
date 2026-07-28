from django.db import models

from apps.reports.models import TimeStampedModel


class SubsidyPropertyType(models.TextChoices):
    HOME = "home", "Home (Private home)"
    VVE = "vve", "Homeowners Association (Apartment / VvE)"
    RENTAL = "rental", "Rental property (Investment / rental)"
    COMMERCIAL = "commercial", "Commercial building"
    OWNER_OCCUPIED = "owner_occupied", "Owner occupied"


class ConstructionYearPeriod(models.TextChoices):
    BEFORE_1920 = "before_1920", "Before 1920"
    Y1920_1945 = "1920_1945", "1920 - 1945"
    Y1946_1970 = "1946_1970", "1946 - 1970"
    Y1971_1990 = "1971_1990", "1971 - 1990"
    Y1991_2010 = "1991_2010", "1991 - 2010"
    AFTER_2010 = "after_2010", "After 2010"


class SubsidyScanRequest(TimeStampedModel):
    """
    Maps to the "Discover in 2 minutes which subsidies are available to
    you" form (Subsidiescan).
    """

    # --- 1. About you ---
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30)
    property_address = models.CharField(
        max_length=255, help_text="Street name and house number"
    )
    postal_code = models.CharField(max_length=10)
    place_of_residence = models.CharField(max_length=100)

    # --- 2. About the property ---
    property_type = models.CharField(
        max_length=20,
        choices=SubsidyPropertyType.choices,
        default=SubsidyPropertyType.HOME,
    )
    construction_year_period = models.CharField(
        max_length=20,
        choices=ConstructionYearPeriod.choices,
        blank=True,
    )
    is_own_property = models.BooleanField(
        default=True,
        help_text="Is the property your property?",
    )

    # --- 3. Other information ---
    reported_damage_before = models.BooleanField(
        help_text="Have you reported damage before?"
    )
    received_decision = models.BooleanField(
        null=True,
        blank=True,
        help_text="Have you already received a decision? (optional)",
    )
    comments = models.TextField(blank=True)

    privacy_policy_accepted = models.BooleanField(default=False)

    # Internal follow-up state, not shown on the form itself but useful
    # for staff triage (mirrors the "we contact you within 1 business
    # day" promise on the page).
    is_contacted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Subsidy scan request"

    def __str__(self) -> str:
        return f"Subsidy scan for {self.full_name} ({self.email})"