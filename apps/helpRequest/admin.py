from django.contrib import admin
from .models import HelpRequest, HelpRequestAttachment


class HelpRequestAttachmentInline(admin.TabularInline):
    model = HelpRequestAttachment
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_number",
        "full_name",
        "email",
        "phone_number",
        "help_type",
        "contact_preference",
        "privacy_policy_accepted",
        "created_at",
    ]
    list_filter = ["help_type", "contact_preference", "privacy_policy_accepted", "created_at"]
    search_fields = ["request_number", "full_name", "email", "phone_number", "address", "description"]
    readonly_fields = ["request_number", "created_at", "updated_at"]
    inlines = [HelpRequestAttachmentInline]


@admin.register(HelpRequestAttachment)
class HelpRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "help_request", "file", "created_at"]
    search_fields = ["help_request__request_number", "help_request__full_name"]
    readonly_fields = ["created_at"]
