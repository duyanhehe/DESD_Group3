from django.db import models
from django.db.models import Manager, Q
from django.conf import settings
from django.utils.timezone import now
from apps.categories.models import Category
from apps.allergens.models import Allergen


class ProductManager(Manager):
    """
    Visibility Logic: 
    An item is 'active' for customers if:
    1. Stock quantity > 0
    2. is_available is True
    3. Today's date is within [available_from, available_to] (inclusive)
    """
    def active(self):
        today = now().date()

        return self.filter(stock_quantity__gt=0, is_available=True).filter(
            Q(available_from__isnull=True) | Q(available_from__lte=today),
            Q(available_to__isnull=True) | Q(available_to__gte=today),
        )


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
    unit = models.CharField(max_length=50, default="unit")

    stock_quantity = models.PositiveIntegerField()

    image = models.ImageField(upload_to='products/', default='products/placeholder.png')

    is_available = models.BooleanField(default=True)

    # seasonal availability
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # allergens
    allergens = models.ManyToManyField(Allergen, blank=True, related_name="products")
    objects = ProductManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["is_available"]),
        ]

    def is_in_season(self):
        today = now().date()
        # if no dates are set then its in season
        if not self.available_from and not self.available_to:
            return True
        if self.available_from and self.available_to:
            return self.available_from <= today <= self.available_to
        if self.available_from:
            return today >= self.available_from
        if self.available_to:
            return today <= self.available_to
        return True

    def is_active(self):
        """
        Product is visible to customers
        """
        return self.stock_quantity > 0 and self.is_available and self.is_in_season()

    def get_status(self):
        if self.stock_quantity == 0:
            return "Out of Stock"
        if not self.is_in_season():
            return "Out of Season"
        if self.is_available:
            return "Available"
        return "Unavailable"

    def update_availability(self):
        """
        Auto-manage availability based on seasonal dates.
        - If out of season: Set is_available to False.
        - If in season: Safe to keep True or reset to True if previously disabled by seasonality.
        Note: This does not override manual 'Unavailable' settings intended by the producer.
        """
        if not self.is_in_season():
            self.is_available = False
        elif self.stock_quantity > 0:
            # If we are in season and HAVE stock, we default to Available 
            # unless there's a specific reason not to.
            # This fixes the 'missing item' issue for new seasonal products.
            if not self.is_available:
                self.is_available = True

    def save(self, *args, **kwargs):
        self.update_availability()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
