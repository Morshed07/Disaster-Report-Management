from rest_framework import serializers
from .models import DamageReport, DamageReportAttachment, CaseUpdate, CaseStatus


class DamageReportAttachmentSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()

    class Meta:
        model = DamageReportAttachment
        fields = ["id", "file", "filename", "created_at"]

    def get_filename(self, obj) -> str:
        if obj.file:
            import os
            return os.path.basename(obj.file.name)
        return ""


class CaseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseUpdate
        fields = ["id", "status", "note", "created_at"]


class DamageReportSerializer(serializers.ModelSerializer):
    attachments = DamageReportAttachmentSerializer(many=True, read_only=True)
    updates = CaseUpdateSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = DamageReport
        fields = [
            "case_number",
            "name",
            "email",
            "phone_number",
            "address",
            "city",
            "postcode",
            "building_type",
            "applicable_case",
            "description",
            "contact_preference",
            "privacy_policy_accepted",
            "status",
            "submitted_at",
            "updated_at",
            "attachments",
            "updates",
        ]

    def get_status(self, obj) -> str:
        # Get the status of the latest update timeline entry
        latest_update = obj.updates.order_by("-created_at").first()
        if latest_update:
            return latest_update.status
        return CaseStatus.RECEIVED


class DamageReportCreateSerializer(serializers.ModelSerializer):
    case_number = serializers.CharField(read_only=True)

    class Meta:
        model = DamageReport
        fields = [
            "case_number",
            "name",
            "email",
            "phone_number",
            "address",
            "city",
            "postcode",
            "building_type",
            "applicable_case",
            "description",
            "contact_preference",
            "privacy_policy_accepted",
        ]

    def validate_description(self, value):
        if len(value) < 20:
            raise serializers.ValidationError(
                "Description must be at least 20 characters long."
            )
        return value

    def validate_privacy_policy_accepted(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the privacy policy to submit a report."
            )
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        damage_report = DamageReport.objects.create(**validated_data)

        # Create initial "received" status update
        CaseUpdate.objects.create(
            damage_report=damage_report,
            status=CaseStatus.RECEIVED,
            note='Application recieved. You have recieved a confirmation email.'
        )

        if request and request.FILES:
            # Supports both 'files' and 'attachments' as upload key names
            files = request.FILES.getlist("files") or request.FILES.getlist(
                "attachments"
            )
            for file in files:
                DamageReportAttachment.objects.create(
                    damage_report=damage_report, file=file
                )

        return damage_report
