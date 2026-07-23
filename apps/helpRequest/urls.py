from django.urls import path
from .views import (
    HelpRequestCreateAPIView,
    HelpRequestListAPIView,
    HelpRequestDetailAPIView,
)

urlpatterns = [
    path("", HelpRequestCreateAPIView.as_view(), name="help-request-create"),
    path("list/", HelpRequestListAPIView.as_view(), name="help-request-list"),
    path("<str:request_number>/", HelpRequestDetailAPIView.as_view(), name="help-request-detail"),
]
