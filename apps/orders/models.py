from django.db import models
from django.conf import settings
from apps.products.models import Product


class CartManager(models.Manager):
    """Custom manager for Cart model with food miles support."""

    def get_queryset(self):
        # Prefetch related data to minimize queries
        return super().get_queryset().prefetch_related(
            "items", "items__product", "items__product__producer"
        )


class Cart(models.Model):
    """Shopping cart — one per logged-in customer, persists across sessions."""

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CartManager()

    @property
    def total_food_miles(self):
        """
        Calculate total food miles for all items in the cart.
        Returns sum of all food miles, or None if any item cannot be calculated.
        """
        total = 0.0
        has_valid_miles = False

        for item in self.items.all():
            miles = item.food_miles
            if miles is not None:
                total += miles
                has_valid_miles = True

        return round(total, 1) if has_valid_miles else None

    def __str__(self):
        return f"Cart #{self.pk} — {self.customer.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # same product shouldn't appear twice in one cart
        unique_together = ("cart", "product")

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    @property
    def food_miles(self):
        """
        Calculate the distance from producer to customer.
        Returns distance in miles or None if calculation fails.
        """
        from apps.logistics.utils import calculate_distance_between_postcodes

        customer = self.cart.customer
        producer = self.product.producer

        # Get postcodes from profiles
        customer_profile = getattr(customer, "customer_profile", None)
        producer_profile = getattr(producer, "producer_profile", None)

        customer_postcode = customer_profile.postcode if customer_profile else None
        producer_postcode = producer_profile.postcode if producer_profile else None

        if not customer_postcode or not producer_postcode:
            return None

        return calculate_distance_between_postcodes(producer_postcode, customer_postcode)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class Order(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (READY, "Ready"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]

    # which transitions are allowed from each status
    VALID_TRANSITIONS = {
        PENDING: [CONFIRMED, CANCELLED],
        CONFIRMED: [READY, CANCELLED],
        READY: [DELIVERED, CANCELLED],
        DELIVERED: [],  # terminal state
        CANCELLED: [],  # terminal state
    }

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    parent_order = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sub_orders",
    )
    producer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="received_orders",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def save(self, *args, **kwargs):
        from django.utils.timezone import now
        if self.status == self.DELIVERED and not self.delivered_at:
            self.delivered_at = now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.pk} — {self.customer.username} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # store producer separately so we can query by producer later
    producer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sold_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order.pk})"


class OrderStatusLog(models.Model):
    """Audit trail — every status change gets logged here."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_logs"
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    note = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Order #{self.order.pk}: {self.old_status} → {self.new_status}"
