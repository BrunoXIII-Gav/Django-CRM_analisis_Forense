import uuid
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from website.forensics.context import client_ip, current_context
from website.forensics.middleware import ForensicContextMiddleware
from website.models import AuditEvent
from website.tests_forensic import DATOS


class ContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("operator", password="x")
        self.client.force_login(self.user)

    def test_uuid_context_secrets_and_response_correlation(self):
        response = self.client.post("/api/records/", DATOS, content_type="application/json",
                                    HTTP_USER_AGENT="x" * 500, HTTP_AUTHORIZATION="secret-token",
                                    HTTP_X_REQUEST_ID="forged", REMOTE_ADDR="10.0.0.1")
        event = AuditEvent.objects.get()
        self.assertEqual(str(uuid.UUID(event.request_id)), response["X-Request-ID"])
        uuid.UUID(event.correlation_id)
        self.assertEqual(len(event.user_agent), 256)
        self.assertNotIn("secret-token", str(event.before) + str(event.after))
        self.assertNotEqual(event.correlation_id, self.client.session.session_key)
        self.assertIsNone(current_context.get())

    @override_settings(FORENSIC_TRUSTED_PROXIES=["10.0.0.0/24"])
    def test_proxy_uses_rightmost_untrusted_hop(self):
        rf = RequestFactory()
        request = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="192.0.2.99, 203.0.113.8, 10.0.0.2")
        self.assertEqual(client_ip(request), "203.0.113.8")
        request.META["REMOTE_ADDR"] = "198.51.100.3"
        self.assertEqual(client_ip(request), "198.51.100.3")
        request.META["REMOTE_ADDR"] = "invalid"
        self.assertIsNone(client_ip(request))

    def test_context_resets_after_exception_and_session_changes_after_logout(self):
        self.client.post("/record/add/", DATOS)
        old = AuditEvent.objects.get().correlation_id
        self.client.logout()
        self.client.force_login(self.user)
        self.client.post("/record/add/", DATOS)
        self.assertNotEqual(old, AuditEvent.objects.last().correlation_id)
        request = RequestFactory().get("/")
        request.session = self.client.session
        def fail(request):
            raise RuntimeError
        with self.assertRaises(RuntimeError):
            ForensicContextMiddleware(fail)(request)
        self.assertIsNone(current_context.get())
