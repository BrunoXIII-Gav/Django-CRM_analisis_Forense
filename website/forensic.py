"""Preparación forense: captura de contexto y estados anterior/posterior."""
import contextvars
import hashlib
import json
import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.forms.models import model_to_dict

from .models import AuditEvent, Record

_ctx = contextvars.ContextVar("forensic_ctx", default=None)


def _source(path):
    if path.startswith("/api/"):
        return "api"
    if path.startswith("/admin/"):
        return "admin"
    return "web"


def _client_ip(request):
    # REMOTE_ADDR: no se confía en X-Forwarded-For (falsificable) en el laboratorio.
    return request.META.get("REMOTE_ADDR") or None


class ForensicContextMiddleware:
    """Guarda cuenta, IP, sesión y origen de la solicitud en curso."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_key = request.session.session_key or ""
        token = _ctx.set({
            "request": request,
            "ip": _client_ip(request),
            "correlation_id": (
                hashlib.sha256(session_key.encode()).hexdigest()[:16]
                if session_key else ""
            ),
            "request_id": str(uuid.uuid4()),
            "source": _source(request.path),
        })
        try:
            return self.get_response(request)
        finally:
            _ctx.reset(token)


def _snapshot(instance):
    data = model_to_dict(instance)
    data["created_at"] = instance.created_at
    data["updated_at"] = instance.updated_at
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _write(action, instance, before, after, using):
    ctx = _ctx.get() or {}
    request = ctx.get("request")
    user = getattr(request, "user", None)
    authenticated = bool(user and user.is_authenticated)
    AuditEvent.objects.using(using).create(
        username=user.get_username() if authenticated else "",
        user_id=user.pk if authenticated else None,
        ip_address=ctx.get("ip"),
        correlation_id=ctx.get("correlation_id", ""),
        request_id=ctx.get("request_id", ""),
        source=ctx.get("source", ""),
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        before=before,
        after=after,
    )


def _pre_save(sender, instance, using, raw=False, **kwargs):
    if raw:
        return  # No consultar otras tablas mientras se cargan fixtures.
    old = (
        sender.objects.using(using).select_for_update().filter(pk=instance.pk).first()
        if instance.pk is not None else None
    )
    instance._audit_before = _snapshot(old) if old else None


def _post_save(sender, instance, created, using, raw=False, **kwargs):
    if raw:
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
    # El objeto en memoria puede contener cambios que nunca se guardaron.
    old = sender.objects.using(using).select_for_update().filter(pk=instance.pk).first()
    instance._audit_before = _snapshot(old) if old else None


def _post_delete(sender, instance, using, **kwargs):
    before = getattr(instance, "_audit_before", None)
    if before is not None:
        _write("DELETE", instance, before, None, using)


def connect():
    pre_save.connect(_pre_save, sender=Record, dispatch_uid="forensic_pre_save")
    post_save.connect(_post_save, sender=Record, dispatch_uid="forensic_post_save")
    pre_delete.connect(_pre_delete, sender=Record, dispatch_uid="forensic_pre_delete")
    post_delete.connect(_post_delete, sender=Record, dispatch_uid="forensic_post_delete")
