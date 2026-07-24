# ActiveCampaign Handover & Webhook Instructions

Here is the draft message and technical instructions you can copy and send to your client (**Julian035**):

***

**Hi Julian,**

Thanks for sharing the ActiveCampaign API credentials. I have set up the integration on the backend. 

Here is what we have done with the API access:
1. **Pipeline & Stage IDs**: We successfully retrieved the IDs for the **Schadecheck** and **Subsidiescan** pipelines, and configured them to automatically create deals in the **"Nieuwe lead"** stages.
2. **Case Number Custom Field**: We checked your custom fields, and since a "Case Number" deal field didn't exist yet, we automatically created it via the API. Its ID is `2`. When a user submits a form on the website, this field will be populated with our internal case number (e.g., `BN-2026-XXXXXX`).
3. **Dutch Stage Mapping**: We mapped the Dutch stage names from your ActiveCampaign account (like *"Adres aangemeld IMG"*, *"Schade-opname ingepland"*, and *"Schadebedrag uitbetaald en factuur gestuurd"*) to the corresponding status options on our website case tracking timeline.

---

### What you need to do now:

To finalize the integration and enable two-way sync, **please configure the webhook in your ActiveCampaign account**:

1. Log in to your **ActiveCampaign** dashboard.
2. Navigate to **Settings** $\rightarrow$ **Developer** $\rightarrow$ **Webhooks**.
3. Click the **Add a Webhook** button.
4. Set the **URL** to (replace `<your-website-domain>` with the actual URL/domain where the backend is hosted):
   ```text
   https://<your-website-domain>/api/v1/webhooks/activecampaign/?secret=bevingshulpnoord-webhook-secret-2026
   ```
5. Set the **Event** to check/trigger on **"Deal stage change"**.
6. Save the Webhook.

### How to test:
Once you have saved the webhook, please:
*   Submit a test **Damage Report** on the website, and check if a new Contact and Deal are created in your ActiveCampaign **"Nieuwe lead schadecheck"** stage with the correct **Case Number** custom field populated.
*   Move that deal to a stage like **"Schade-opname ingepland"** in ActiveCampaign, and verify that the status updates automatically on the website's case status tracking page.
