"""
ActiveCampaign CRM integration client.

Wraps the ActiveCampaign REST API v3 for outbound sync (creating contacts
and deals when forms are submitted) and provides helpers used by the
inbound webhook handler.

All configuration is read from ``django.conf.settings`` and is env-driven
so nothing needs to be hard-coded.  If the API URL or key are blank the
client silently no-ops, which keeps local dev safe.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ActiveCampaignError(Exception):
    """Raised when any ActiveCampaign API call fails."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ActiveCampaignClient:
    """
    Thin wrapper around the ActiveCampaign v3 REST API.

    Usage::

        client = ActiveCampaignClient()
        contact_id = client.create_or_update_contact(
            email="user@example.com",
            first_name="Jan",
            last_name="De Vries",
            phone="+31612345678",
        )
        deal_id = client.create_deal(
            title="BN-2026-123456 — Jan De Vries",
            contact_id=contact_id,
            pipeline_id=settings.ACTIVECAMPAIGN_SCHADECHECK_PIPELINE_ID,
            stage_id=settings.ACTIVECAMPAIGN_NEW_LEADS_STAGE_ID,
            case_number="BN-2026-123456",
        )
    """

    def __init__(self):
        self.api_url = getattr(settings, "ACTIVECAMPAIGN_API_URL", "").rstrip("/")
        self.api_key = getattr(settings, "ACTIVECAMPAIGN_API_KEY", "")
        self.case_number_field_id = getattr(
            settings, "ACTIVECAMPAIGN_CASE_NUMBER_FIELD_ID", ""
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    @property
    def _headers(self) -> dict:
        return {
            "Api-Token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """
        Fire an HTTP request against the AC API and return the parsed JSON.

        Raises ``ActiveCampaignError`` on any non-2xx response or network
        error so callers can catch it in one place.
        """
        url = f"{self.api_url}/api/3/{path.lstrip('/')}"
        try:
            resp = requests.request(
                method, url, headers=self._headers, timeout=15, **kwargs
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise ActiveCampaignError(
                f"ActiveCampaign API error ({method} {path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_or_update_contact(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
    ) -> str | None:
        """
        Create or update a Contact in ActiveCampaign.

        Uses the ``contact/sync`` endpoint which upserts by email.
        Returns the contact ID (as a string) or ``None`` if the client
        is not configured.
        """
        if not self._is_configured:
            logger.info("ActiveCampaign not configured — skipping contact sync.")
            return None

        payload = {
            "contact": {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "phone": phone,
            }
        }
        data = self._request("POST", "contact/sync", json=payload)
        contact_id = data.get("contact", {}).get("id")
        logger.info("AC contact synced → id=%s for %s", contact_id, email)
        return contact_id

    def create_deal(
        self,
        title: str,
        contact_id: str,
        pipeline_id: str,
        stage_id: str,
        case_number: str = "",
    ) -> str | None:
        """
        Create a new Deal in ActiveCampaign and optionally write our
        ``case_number`` into a custom field on the deal.

        Returns the deal ID (string) or ``None`` if not configured.
        """
        if not self._is_configured:
            logger.info("ActiveCampaign not configured — skipping deal creation.")
            return None

        payload = {
            "deal": {
                "title": title,
                "contact": contact_id,
                "pipeline": pipeline_id,
                "stage": stage_id,
                "status": 0,  # 0 = open
            }
        }
        data = self._request("POST", "deals", json=payload)
        deal_id = data.get("deal", {}).get("id")
        logger.info("AC deal created → id=%s title=%s", deal_id, title)

        # Write our case_number into a custom field on the deal so the
        # inbound webhook can match it later.
        if deal_id and case_number and self.case_number_field_id:
            self.update_deal_custom_field(
                deal_id, self.case_number_field_id, case_number
            )

        return deal_id

    def update_deal_custom_field(
        self, deal_id: str, field_id: str, value: str
    ) -> None:
        """
        Set a custom field value on an existing Deal.
        """
        if not self._is_configured:
            return

        payload = {
            "dealCustomFieldDatum": {
                "dealId": deal_id,
                "customFieldId": int(field_id),
                "fieldValue": value,
            }
        }
        self._request("POST", "dealCustomFieldData", json=payload)
        logger.info(
            "AC deal %s custom field %s set to %s", deal_id, field_id, value
        )
