from django.urls import path
from .views import GoogleReviewsAPIView, GoogleReviewWriteUrlAPIView

urlpatterns = [
    path("google/", GoogleReviewsAPIView.as_view(), name="google-reviews"),
    path("google/write-url/", GoogleReviewWriteUrlAPIView.as_view(), name="google-reviews-write-url"),
]
