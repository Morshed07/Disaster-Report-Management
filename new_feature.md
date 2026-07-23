# Feature Brief: ActiveCampaign CRM Integration

## Context

We have a Django + DRF backend for "Bevingshulp Noord" (earthquake damage
relief intermediary, Groningen, NL). It has two public lead-generation
forms:

1. **Damage Report form** → creates a `DamageReport` (app: `damage_reports`,
   model in `damage_reports/models.py`), which generates a unique
   `case_number` (format `BN-2026-XXXXXX`) and tracks a `status` field
   (`received`, `under_review`, `in_progress`, `approved`, `completed`)
   with a related `CaseUpdate` timeline.
2. **Subsidy Scan form** → creates a `SubsidyScanRequest`
   (`damage_reports/subsidy_models.py`).

The client manages sales/case progress in **ActiveCampaign** (CRM), using
a 10-stage Deal pipeline:

**Phase 1 — Prospecting & Qualification (internal only, not shown on our site):**
1. New Leads
2. First Contact
3. No Contact (Second Attempt)
4. Inspection Appointment Scheduled
5. Disqualified

**Phase 2 — Active Case Management (must sync to our website's Case Status page):**
6. Client / Contract Signed — case number is finalized here
7. Earthquake Damage Reported
8. State Inspection at Property
9. Waiting for Report
10. Invoice Processed / Payout

ActiveCampaign docs: https://developers.activecampaign.com/
Webhooks docs: https://developers.activecampaign.com/page/webhooks

## Goal

Build a two-way integration between our Django backend and ActiveCampaign:

### 1. Outbound sync (Website → ActiveCampaign)
When a `DamageReport` or `SubsidyScanRequest` is created via our existing
APIViews, call the ActiveCampaign API to:
- Create or update a **Contact** (name, email, phone).
- Create a **Deal** attached to that contact, placed in **Stage 1 (New
  Leads)** of the correct pipeline (Schadecheck pipeline for damage
  reports; a separate Subsidiescan pipeline for subsidy scans).
- Write our internal `case_number` into a custom field on the
  Contact/Deal in ActiveCampaign so the two records can be matched later.

This should run synchronously right after `serializer.save()` in the
relevant APIView, wrapped so that an ActiveCampaign failure does NOT
block the form submission response to the user (log the error, but the
user still gets their confirmation/case number).

### 2. Inbound sync (ActiveCampaign → Website)
Build a webhook receiver endpoint (e.g. `POST /api/v1/webhooks/activecampaign/`)
that:
- Verifies the request is genuinely from ActiveCampaign (per their
  webhook docs — check for any signature/secret verification available).
- Parses the incoming payload for the Deal ID and its new stage.
- Looks up the matching `DamageReport` via the case number stored on the
  Deal (or via a stored `activecampaign_deal_id` field — add this field
  to the model if it doesn't exist).
- Only stages 6–10 should affect our site. Map them to our `CaseStatus`
  choices like this:

  | ActiveCampaign Stage              | Our `CaseStatus`   |
  |------------------------------------|--------------------|
  | Client / Contract Signed           | `received`         |
  | Earthquake Damage Reported         | `under_review`      |
  | State Inspection at Property       | `in_progress`       |
  | Waiting for Report                 | `in_progress`       |
  | Invoice Processed / Payout         | `completed`         |

  (Confirm exact mapping/wording is still correct before finalizing.)

- Updates `DamageReport.status` and creates a new `CaseUpdate` entry with
  an appropriate note, so it shows up in the case status timeline.
- Ignore/no-op webhook events for stages 1–5 or unrelated pipelines.
- Return a 200 quickly (ActiveCampaign expects a fast response); do any
  slow work asynchronously if needed.

## What to build

1. `damage_reports/integrations/activecampaign.py`
   - A small client class/service wrapping the AC REST API
     (`api_url`, `api_key` from Django settings/env vars).
   - Methods: `create_or_update_contact(...)`, `create_deal(...)`,
     `update_deal_custom_field(...)`.
   - Use `requests`, handle non-200 responses gracefully, raise a custom
     `ActiveCampaignError` that callers can catch.

2. Hook the outbound calls into `DamageReportCreateAPIView.post()` and
   `SubsidyScanRequestAPIView.post()` in `damage_reports/views.py`,
   wrapped in try/except so failures are logged, not raised to the user.

3. `damage_reports/webhooks.py` (or a new view in `views.py`):
   - `ActiveCampaignWebhookAPIView` (APIView, `POST`, no auth required
     but validate a shared secret/signature if AC provides one).
   - Parsing + stage-mapping + status/timeline update logic described
     above.

4. Add to `urls.py`: `path("webhooks/activecampaign/", ActiveCampaignWebhookAPIView.as_view())`.

5. Settings additions (env-driven, do not hardcode):
   ```
   ACTIVECAMPAIGN_API_URL
   ACTIVECAMPAIGN_API_KEY
   ACTIVECAMPAIGN_SCHADECHECK_PIPELINE_ID
   ACTIVECAMPAIGN_SUBSIDIESCAN_PIPELINE_ID
   ACTIVECAMPAIGN_STAGE_IDS  (dict/mapping of stage name -> AC stage ID)
   ACTIVECAMPAIGN_CASE_NUMBER_FIELD_ID
   ACTIVECAMPAIGN_WEBHOOK_SECRET  (if applicable)
   ```
   Reference `.env` variables via `django-environ` or `os.environ`,
   whichever this project already uses — check existing `settings.py`
   first.

6. Add model field(s) if missing:
   - `DamageReport.activecampaign_deal_id` (nullable CharField) to make
     inbound lookups reliable even if case_number matching is fragile.

7. Write basic tests:
   - Outbound: mock the AC API, assert `create_or_update_contact` and
     `create_deal` are called with expected payload when a `DamageReport`
     is created.
   - Inbound: POST a sample webhook payload (use a fixture matching the
     real AC webhook format), assert `DamageReport.status` and a new
     `CaseUpdate` are created correctly; assert stages 1–5 are ignored.

## Open items to confirm before/while building (do not guess — ask or stub with TODO + settings placeholder)

- Actual ActiveCampaign API URL, API key, pipeline IDs, stage IDs, and
  custom field ID (not yet provided by client).
- Exact webhook payload structure/field names (fetch a real sample from
  the client's AC account — do not assume field names beyond what AC's
  public docs show).
- Whether webhook signature verification is available/required.
- Final stage → CaseStatus wording mapping, pending client confirmation.

## Constraints

- Keep using DRF `APIView` (not generic/viewsets) to match the existing
  codebase style in `damage_reports/views.py`.
- Keep the AC integration isolated in its own module so it can be
  mocked/disabled easily in tests and local dev.
- Do not break existing endpoints or serializers — only add to them.