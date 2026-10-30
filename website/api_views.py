from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Record
from .serializers import RecordSerializer
from .forensics import services


class RecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for CRUD operations on customer records.

    list:    GET    /api/records/
    create:  POST   /api/records/
    read:    GET    /api/records/{id}/
    update:  PUT    /api/records/{id}/
    partial: PATCH  /api/records/{id}/
    delete:  DELETE /api/records/{id}/
    """

    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name", "email", "phone", "city"]

    def perform_create(self, serializer):
        serializer.instance = services.create_record(serializer.validated_data, request=self.request)

    def perform_update(self, serializer):
        serializer.instance = services.update_record(serializer.instance.pk, serializer.validated_data, request=self.request)

    def perform_destroy(self, instance):
        services.delete_record(instance.pk, request=self.request)
