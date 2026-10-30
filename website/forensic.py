"""Compatibility signals for legacy ORM callers; HTTP uses the shared service.

Signals skip service-owned writes, preventing duplicate events. QuerySet.update,
bulk inserts and raw SQL remain outside the documented coverage.
"""
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save

from .models import Record
from .forensics.context import current_context as _ctx, service_active
from .forensics.middleware import ForensicContextMiddleware
from .forensics.snapshots import snapshot as _snapshot
from .forensics.services import write_event as _write


def _pre_save(sender, instance, using, raw=False, **kwargs):
    if raw or service_active.get():
        return  # No consultar otras tablas mientras se cargan fixtures.
    old = (
        sender.objects.using(using).select_for_update().filter(pk=instance.pk).first()
        if instance.pk is not None else None
    )
    instance._audit_before = _snapshot(old) if old else None


def _post_save(sender, instance, created, using, raw=False, **kwargs):
    if raw or service_active.get():
        return
    # Leer lo persistido: update_fields y expresiones F pueden diferir del objeto.
    saved = sender.objects.using(using).get(pk=instance.pk)
    _write(
        "CREATE" if created else "UPDATE",
        instance,
        None if created else getattr(instance, "_audit_before", None),
        _snapshot(saved),
        using,
    )


def _pre_delete(sender, instance, using, **kwargs):
    if service_active.get():
        return
    # El objeto en memoria puede contener cambios que nunca se guardaron.
    old = sender.objects.using(using).select_for_update().filter(pk=instance.pk).first()
    instance._audit_before = _snapshot(old) if old else None


def _post_delete(sender, instance, using, **kwargs):
    if service_active.get():
        return
    before = getattr(instance, "_audit_before", None)
    if before is not None:
        _write("DELETE", instance, before, None, using)


def connect():
    pre_save.connect(_pre_save, sender=Record, dispatch_uid="forensic_pre_save")
    post_save.connect(_post_save, sender=Record, dispatch_uid="forensic_post_save")
    pre_delete.connect(_pre_delete, sender=Record, dispatch_uid="forensic_pre_delete")
    post_delete.connect(_post_delete, sender=Record, dispatch_uid="forensic_post_delete")
