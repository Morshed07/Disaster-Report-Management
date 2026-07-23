from rest_framework import serializers

from .models import SubsidyScanRequest


# ---------------------------------------------------------------------------
# Subsidy scan form — write side ("Discover in 2 minutes which subsidies
# are available to you")
# ---------------------------------------------------------------------------
class SubsidyScanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubsidyScanRequest
        fields = [
            "id",
            # 1. About you
            "full_name",
            "email",
            "phone_number",
            "property_address",
            "postal_code",
            "place_of_residence",
            # 2. About the property
            "property_type",
            "construction_year_period",
            "is_own_property",
            # 3. Other information
            "reported_damage_before",
            "received_decision",
            "comments",
            "privacy_policy_accepted",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_privacy_policy_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must agree to the privacy statement to request a subsidy scan."
            )
        return value


# ---------------------------------------------------------------------------
# Confirmation response returned right after submitting the form
# ---------------------------------------------------------------------------
class SubsidyScanRequestConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubsidyScanRequest
        fields = ["id", "email", "created_at"]
        read_only_fields = fields
