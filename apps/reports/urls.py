from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DamageReportViewSet

router = DefaultRouter()
router.register(r"reports", DamageReportViewSet, basename="report")

urlpatterns = [
    path("", include(router.urls)),
]