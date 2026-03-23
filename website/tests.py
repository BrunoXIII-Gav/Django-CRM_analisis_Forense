from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Record


class RecordModelTest(TestCase):
    """Tests for the Record model."""

    def setUp(self):
        self.record = Record.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+11234567890",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zipcode="62704",
        )

    def test_str_representation(self):
        self.assertEqual(str(self.record), "John Doe")

    def test_record_has_timestamps(self):
        self.assertIsNotNone(self.record.created_at)
        self.assertIsNotNone(self.record.updated_at)

    def test_default_ordering(self):
        older = Record.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            phone="+10987654321",
            address="456 Oak Ave",
            city="Portland",
            state="OR",
            zipcode="97201",
        )
        records = list(Record.objects.all())
        # Most recent first
        self.assertEqual(records[0], older)


class AuthViewsTest(TestCase):
    """Tests for authentication views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(
            reverse("home"),
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertRedirects(response, reverse("home"))

    def test_login_failure(self):
        response = self.client.post(
            reverse("home"),
            {"username": "testuser", "password": "wrongpass"},
        )
        self.assertRedirects(response, reverse("home"))

    def test_logout(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("home"))

    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_register_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())


class RecordCRUDViewsTest(TestCase):
    """Tests for record CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.record = Record.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+11234567890",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zipcode="62704",
        )

    def test_view_record_requires_login(self):
        response = self.client.get(reverse("record", args=[self.record.pk]))
        self.assertRedirects(response, f"{reverse('home')}?next={reverse('record', args=[self.record.pk])}")

    def test_view_record_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("record", args=[self.record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John")

    def test_view_record_404(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("record", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_add_record_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("add_record"),
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "phone": "+10987654321",
                "address": "456 Oak Ave",
                "city": "Portland",
                "state": "OR",
                "zipcode": "97201",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Record.objects.count(), 2)

    def test_delete_record_requires_post(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("delete_record", args=[self.record.pk]))
        self.assertEqual(response.status_code, 405)

    def test_delete_record_post(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("delete_record", args=[self.record.pk]))
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Record.objects.count(), 0)

    def test_update_record_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("update_record", args=[self.record.pk]),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
                "phone": "+11234567890",
                "address": "789 New St",
                "city": "Chicago",
                "state": "IL",
                "zipcode": "60601",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.record.refresh_from_db()
        self.assertEqual(self.record.first_name, "Updated")

    def test_search_records(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("home"), {"q": "John"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John")


class RecordAPITest(TestCase):
    """Tests for the REST API."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="apiuser", password="testpass123"
        )
        self.record = Record.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+11234567890",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zipcode="62704",
        )

    def test_api_requires_auth(self):
        response = self.client.get("/api/records/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_list_records(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/records/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_create_record(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "first_name": "API",
            "last_name": "User",
            "email": "api@example.com",
            "phone": "+19876543210",
            "address": "API Street",
            "city": "API City",
            "state": "CA",
            "zipcode": "90210",
        }
        response = self.client.post("/api/records/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Record.objects.count(), 2)

    def test_api_retrieve_record(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/records/{self.record.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "John")

    def test_api_update_record(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/records/{self.record.pk}/",
            {"first_name": "Updated"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.record.refresh_from_db()
        self.assertEqual(self.record.first_name, "Updated")

    def test_api_delete_record(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/records/{self.record.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Record.objects.count(), 0)
