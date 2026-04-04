from django.db import models
from django.conf import settings


class Product(models.Model):
    producer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products"
    )

    name = models.CharField(max_length=255)
    description = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    stock_quantity = models.PositiveIntegerField()

    is_available = models.BooleanField(default=True)

    # seasonal availability
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_in_season(self):
        from django.utils.timezone import now

        today = now().date()
        if self.available_from and self.available_to:
            return self.available_from <= today <= self.available_to
        return True

    def __str__(self):
        return self.name
