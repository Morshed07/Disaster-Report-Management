import os
from rest_framework import serializers
from .models import HelpRequest, HelpRequestAttachment, HelpType, ContactPreference


class HelpRequestAttachmentSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()

    class Meta:
        model = HelpRequestAttachment
        fields = ["id", "file", "filename", "created_at"]

    def get_filename(self, obj) -> str:
        if obj.file:
            return os.path.basename(obj.file.name)
        return ""


class HelpRequestSerializer(serializers.ModelSerializer):
    attachments = HelpRequestAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = HelpRequest
        fields = [
            "id",
            "request_number",
            "full_name",
            "email",
            "phone_number",
            "address",
            "help_type",
            "description",
            "contact_preference",
            "privacy_policy_accepted",
            "created_at",
            "updated_at",
            "attachments",
        ]
        read_only_fields = ["id", "request_number", "created_at", "updated_at"]


class HelpRequestCreateSerializer(serializers.ModelSerializer):
    request_number = serializers.CharField(read_only=True)

    class Meta:
        model = HelpRequest
        fields = [
            "request_number",
            "full_name",
            "email",
            "phone_number",
            "address",
            "help_type",
            "description",
            "contact_preference",
            "privacy_policy_accepted",
        ]

    def validate_description(self, value: str) -> str:
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Description must be at least 20 characters long."
            )
        return value

    def validate_privacy_policy_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must agree to the privacy policy to submit a request."
            )
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        help_request = HelpRequest.objects.create(**validated_data)

        if request and request.FILES:
            files = request.FILES.getlist("attachments") or request.FILES.getlist("files")
            for file in files:
                HelpRequestAttachment.objects.create(
                    help_request=help_request, file=file
                )

        return help_request


class HelpRequestConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequest
        fields = ["id", "request_number", "full_name", "email", "created_at"]
        read_only_fields = fields
