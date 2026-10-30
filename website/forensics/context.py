import contextvars
import ipaddress
import uuid

from django.conf import settings

current_context = contextvars.ContextVar("forensic_context", default=None)
service_active = contextvars.ContextVar("forensic_service_active", default=False)
SESSION_KEY = "forensic_correlation_id"


def channel(path):
    if path.startswith("/api/"):
        return "api"
    if path.startswith("/admin/"):
        return "admin"
    return "web"


def client_ip(request):
    try:
        remote = ipaddress.ip_address(request.META.get("REMOTE_ADDR", ""))
    except ValueError:
        return None
    trusted = [ipaddress.ip_network(net) for net in settings.FORENSIC_TRUSTED_PROXIES]
    if any(remote in net for net in trusted):
        # Walk right to left, discarding only explicitly trusted proxy hops.
        try:
            hops = [ipaddress.ip_address(part.strip()) for part in
                    request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")]
        except ValueError:
            return str(remote)
        for hop in reversed(hops):
            remote = hop
            if not any(hop in net for net in trusted):
                break
    return str(remote)


def request_context(request):
    correlation = request.session.get(SESSION_KEY)
    try:
        uuid.UUID(str(correlation))
    except (ValueError, TypeError, AttributeError):
        correlation = str(uuid.uuid4())
        request.session[SESSION_KEY] = correlation
    return {
        "request": request, "ip": client_ip(request),
        "correlation_id": correlation, "request_id": str(uuid.uuid4()),
        "source": channel(request.path),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:256],
    }
