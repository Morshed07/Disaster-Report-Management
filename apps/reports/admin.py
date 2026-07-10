from django.contrib import admin
from .models import DamageReport, DamageReportAttachment, CaseUpdate


class AttachmentInline(admin.TabularInline):
    model = DamageReportAttachment
    extra = 1
    readonly_fields = ("created_at", "updated_at")


class CaseUpdateInline(admin.TabularInline):
    model = CaseUpdate
    extra = 1
    readonly_fields = ("created_at", "updated_at")


@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ("case_number", "name", "email", "submitted_at")
    list_filter = ("building_type", "applicable_case", "submitted_at")
    search_fields = (
        "case_number",
        "name",
        "email",
        "address",
        "city",
        "postcode",
    )
    ordering = ("-submitted_at",)
    readonly_fields = (
        "id",
        "case_number",
        "submitted_at",
        "created_at",
        "updated_at",
    )
    inlines = [AttachmentInline, CaseUpdateInline]


@admin.register(CaseUpdate)
class CaseUpdateAdmin(admin.ModelAdmin):
    list_display = ("damage_report", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("damage_report__case_number", "note")
    ordering = ("-created_at",)