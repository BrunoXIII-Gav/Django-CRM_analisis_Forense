from django.core.validators import RegexValidator
from django.db import models


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