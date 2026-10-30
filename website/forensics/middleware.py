import json
import logging
from datetime import datetime, timezone

from .context import current_context, request_context

logger = logging.getLogger("website.requests")


class ForensicContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        context = request_context(request)
        request.forensic_context = context
        token = current_context.set(context)
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            response["X-Request-ID"] = context["request_id"]
            return response
        finally:
            # Only controlled route patterns, never query strings, headers or bodies.
            match = getattr(request, "resolver_match", None)
            logger.info(json.dumps({
                "kind": "http", "time_utc": datetime.now(timezone.utc).isoformat(),
                "request_id": context["request_id"], "channel": context["source"],
                "method": request.method, "route": getattr(match, "route", ""),
                "status": status,
            }))
            current_context.reset(token)
