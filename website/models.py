from django.core.validators import RegexValidator
from django.db import models, router, transaction


class Record(models.Model):
    """Customer record in the CRM system."""

    phone_validator = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be 9-15 digits, optionally starting with '+'.",
    )
    zipcode_validator = RegexValidator(
        regex=r"^\d{5}(-\d{4})?$",
        message="Enter a valid US ZIP code (e.g. 12345 or 12345-6789).",
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=15, validators=[phone_validator])
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zipcode = models.CharField(max_length=10, validators=[zipcode_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # El cambio y su evento deben confirmarse o revertirse juntos.
        using = using or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            return super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError("Los eventos de auditoría son inmutables.")

    def delete(self):
        raise PermissionError("Los eventos de auditoría no se pueden eliminar.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise PermissionError("Los eventos de auditoría son inmutables.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise PermissionError("Los eventos de auditoría son inmutables.")
        return super().bulk_create(objs, **kwargs)


class AuditEvent(models.Model):
    """Evento de auditoría con contexto forense (preparación forense)."""

    ACTION_CHOICES = [
        ("CREATE", "Creación"),
        ("UPDATE", "Modificación"),
        ("DELETE", "Eliminación"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    username = models.CharField(max_length=150, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)
    request_id = models.CharField(max_length=36, blank=True)
    source = models.CharField(max_length=10, blank=True)  # web | admin | api
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Los eventos de auditoría son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Los eventos de auditoría no se pueden eliminar.")
