from django.urls import path

from .views import SubsidyScanRequestAPIView

urlpatterns = [
    path(
        "subsidy-scan/",
        SubsidyScanRequestAPIView.as_view(),
        name="subsidy-scan-create",
    ),
]
