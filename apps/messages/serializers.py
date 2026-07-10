from rest_framework import serializers
from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "name",
            "phone_number",
            "email",
            "message",
            "privacy_policy_accepted",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
 
    def validate_privacy_policy_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must agree to the privacy policy to send a message."
            )
        return value