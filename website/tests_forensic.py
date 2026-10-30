from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.test import TestCase

from .models import AuditEvent, Record

DATOS = dict(first_name="Ana", last_name="Prueba", email="ana@lab.test",
             phone="987654321", address="Av. Lab 1", city="Lima",
             state="Lima", zipcode="12345")


class CoberturaForensicaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("empleado1", password="x", is_staff=True,
                                             is_superuser=True)
        self.client.login(username="empleado1", password="x")

    def test_web_crear_modificar_eliminar(self):
        response = self.client.post("/record/add/", DATOS, REMOTE_ADDR="10.0.0.5")
        self.assertEqual(response.status_code, 302)
        r = Record.objects.get()
        self.client.post(f"/record/{r.pk}/update/", {**DATOS, "phone": "900000000"})
        self.client.post(f"/record/{r.pk}/delete/")
        acciones = list(AuditEvent.objects.values_list("action", flat=True))
        self.assertEqual(acciones, ["CREATE", "UPDATE", "DELETE"])
        upd = AuditEvent.objects.get(action="UPDATE")
        self.assertEqual(upd.before["phone"], "987654321")
        self.assertEqual(upd.after["phone"], "900000000")
        self.assertEqual(upd.username, "empleado1")
        self.assertEqual(upd.source, "web")
        self.assertTrue(upd.correlation_id)
        dele = AuditEvent.objects.get(action="DELETE")
        self.assertEqual(dele.before["phone"], "900000000")
        self.assertIsNone(dele.after)
        self.assertEqual(AuditEvent.objects.filter(ip_address="10.0.0.5").count(), 1)

    def test_api_y_correlacion_de_sesion(self):
        self.client.post("/api/records/", DATOS, content_type="application/json")
        r = Record.objects.get()
        self.client.patch(f"/api/records/{r.pk}/", {"city": "Cusco"},
                          content_type="application/json")
        self.client.delete(f"/api/records/{r.pk}/")
        eventos = AuditEvent.objects.all()
        self.assertEqual([e.source for e in eventos], ["api"] * 3)
        self.assertEqual(len({e.correlation_id for e in eventos}), 1)
        self.assertTrue(eventos[0].correlation_id)
        self.assertEqual(len({e.request_id for e in eventos}), 3)
        self.assertEqual({e.user_id for e in eventos}, {self.user.pk})

    def test_admin(self):
        r = Record.objects.create(**DATOS)
        self.client.post(f"/admin/website/record/{r.pk}/change/", {**DATOS, "city": "Piura"})
        e = AuditEvent.objects.filter(source="admin", action="UPDATE").get()
        self.assertEqual((e.before["city"], e.after["city"]), ("Lima", "Piura"))

    def test_limite_update_masivo_sin_cobertura(self):
        Record.objects.create(**DATOS)
        n = AuditEvent.objects.count()
        Record.objects.all().update(city="Tacna")  # SQL directo: no emite señales
        self.assertEqual(AuditEvent.objects.count(), n)

    def test_eventos_inmutables(self):
        Record.objects.create(**DATOS)
        e = AuditEvent.objects.get()
        with self.assertRaises(PermissionError):
            e.delete()
        with self.assertRaises(PermissionError):
            e.save()

    def test_eventos_inmutables_en_queryset(self):
        Record.objects.create(**DATOS)
        e = AuditEvent.objects.get()
        with self.assertRaises(PermissionError):
            AuditEvent.objects.filter(pk=e.pk).update(username="otro")
        with self.assertRaises(PermissionError):
            AuditEvent.objects.all().delete()
        with self.assertRaises(PermissionError):
            AuditEvent.objects.bulk_update([e], ["username"])
        with self.assertRaises(PermissionError):
            AuditEvent.objects.bulk_create(
                [e], update_conflicts=True, update_fields=["username"], unique_fields=["id"]
            )
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_admin_solo_lectura(self):
        Record.objects.create(**DATOS)
        e = AuditEvent.objects.get()
        url = f"/admin/website/auditevent/{e.pk}/change/"
        self.assertEqual(self.client.get("/admin/website/auditevent/").status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"username": "otro"}).status_code, 403)
        self.assertEqual(self.client.get("/admin/website/auditevent/add/").status_code, 403)
        self.assertEqual(
            self.client.post(f"/admin/website/auditevent/{e.pk}/delete/").status_code, 403
        )
        self.client.logout()
        self.assertEqual(self.client.get("/admin/website/auditevent/").status_code, 302)

    def test_admin_crear_y_eliminar(self):
        response = self.client.post("/admin/website/record/add/", DATOS)
        self.assertEqual(response.status_code, 302)
        r = Record.objects.get()
        response = self.client.post(f"/admin/website/record/{r.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(AuditEvent.objects.values_list("action", "source")), [
            ("CREATE", "admin"), ("DELETE", "admin"),
        ])

    def test_snapshot_refleja_solo_campos_persistidos(self):
        r = Record.objects.create(**DATOS)
        r.city = "Cusco"
        r.phone = "900000000"  # No incluido en update_fields.
        r.save(update_fields=["city"])
        e = AuditEvent.objects.get(action="UPDATE")
        self.assertEqual(e.before["city"], "Lima")
        self.assertEqual(e.after["city"], "Cusco")
        self.assertEqual(e.after["phone"], DATOS["phone"])

    def test_snapshot_resuelve_expresiones_de_base_de_datos(self):
        r = Record.objects.create(**DATOS)
        r.city = F("state")
        r.save(update_fields=["city"])
        self.assertEqual(AuditEvent.objects.get(action="UPDATE").after["city"], "Lima")

    def test_eliminacion_captura_estado_persistido(self):
        r = Record.objects.create(**DATOS)
        r.city = "Cusco"  # Cambio en memoria, no guardado.
        r.delete()
        self.assertEqual(AuditEvent.objects.get(action="DELETE").before["city"], "Lima")

    def test_eliminacion_de_objeto_ya_borrado_no_inventa_evento(self):
        r = Record.objects.create(**DATOS)
        obsoleto = Record.objects.get(pk=r.pk)
        r.delete()
        obsoleto.delete()
        self.assertEqual(AuditEvent.objects.filter(action="DELETE").count(), 1)

    def test_fallo_auditoria_revierte_creacion_y_modificacion(self):
        with patch("website.forensic._write", side_effect=RuntimeError("sin auditoría")):
            with self.assertRaises(RuntimeError):
                Record.objects.create(**DATOS)
        self.assertFalse(Record.objects.exists())
        r = Record.objects.create(**DATOS)
        r.city = "Cusco"
        with patch("website.forensic._write", side_effect=RuntimeError("sin auditoría")):
            with self.assertRaises(RuntimeError):
                r.save()
        r.refresh_from_db()
        self.assertEqual(r.city, "Lima")
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_fallo_auditoria_revierte_eliminacion(self):
        r = Record.objects.create(**DATOS)
        with patch("website.forensic._write", side_effect=RuntimeError("sin auditoría")):
            with self.assertRaises(RuntimeError):
                # Aislar del atomic exterior de TestCase; el colector de borrado
                # usa atomic(savepoint=False) y marca su transacción al fallar.
                with transaction.atomic():
                    r.delete()
        self.assertTrue(Record.objects.filter(pk=r.pk).exists())
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_rollback_no_deja_eventos(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Record.objects.create(**DATOS)
                raise RuntimeError("cancelar operación")
        self.assertFalse(Record.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_ip_no_confia_en_forwarded_y_contexto_no_se_filtra(self):
        self.client.post(
            "/record/add/", DATOS, REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="192.0.2.99",
        )
        e = AuditEvent.objects.get()
        self.assertEqual(e.ip_address, "10.0.0.5")
        self.assertEqual(e.username, self.user.username)
        Record.objects.create(**DATOS)
        externo = AuditEvent.objects.order_by("id").last()
        self.assertEqual(externo.username, "")
        self.assertEqual(externo.request_id, "")
        self.assertIsNone(externo.ip_address)

    def test_solicitud_rechazada_no_genera_evento(self):
        self.client.logout()
        response = self.client.post("/api/records/", DATOS, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditEvent.objects.exists())

    def test_borrado_masivo_registra_cada_objeto(self):
        Record.objects.create(**DATOS)
        Record.objects.create(**DATOS)
        Record.objects.all().delete()
        self.assertEqual(AuditEvent.objects.filter(action="DELETE").count(), 2)

    def test_eliminar_usuario_conserva_atribucion(self):
        self.client.post("/record/add/", DATOS)
        user_id = self.user.pk
        self.user.delete()
        e = AuditEvent.objects.get()
        self.assertEqual((e.user_id, e.username), (user_id, "empleado1"))
