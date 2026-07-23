from django.urls import path

from apps.reports.views import ActiveCampaignWebhookAPIView

urlpatterns = [
    path(
        "activecampaign/",
        ActiveCampaignWebhookAPIView.as_view(),
        name="activecampaign-webhook",
    ),
]
