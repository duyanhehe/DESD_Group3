from django.db import models
from django.conf import settings
from django.utils.timezone import now
from categories.models import Category
from allergens.models import Allergen


class Product(models.Model):
    producer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    name = models.CharField(max_length=255)
    description = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default="kg")

    stock_quantity = models.PositiveIntegerField()

    is_available = models.BooleanField(default=True)

    # seasonal availability
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # allergens
    allergens = models.ManyToManyField(Allergen, blank=False, related_name="products")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["is_available"]),
        ]

    def is_in_season(self):
        today = now().date()
        if self.available_from and self.available_to:
            return self.available_from <= today <= self.available_to
        return False

    def is_active(self):
        """
        Product is visible to customers
        """
        return self.stock_quantity > 0 and (self.is_available or self.is_in_season())

    def get_status(self):
        if self.is_available:
            return "Available"
        if self.is_in_season():
            return "In Season"
        return "Unavailable"

    def __str__(self):
        return self.name
