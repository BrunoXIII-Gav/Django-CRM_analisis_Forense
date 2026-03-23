from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import RecordViewSet

router = DefaultRouter()
router.register(r"records", RecordViewSet, basename="record-api")

urlpatterns = [
    path("", include(router.urls)),
]
