from django.contrib import admin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone_number", "is_handled", "created_at")
    list_filter = ("is_handled", "created_at")
    search_fields = ("name", "email", "phone_number", "message")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "name",
        "email",
        "phone_number",
        "message",
        "privacy_policy_accepted",
        "created_at",
        "updated_at",
    )
