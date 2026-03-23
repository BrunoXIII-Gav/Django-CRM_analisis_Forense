from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Record
from .serializers import RecordSerializer


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
