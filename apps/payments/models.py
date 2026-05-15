import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class ProducerWeeklySettlement(models.Model):
    """Weekly settlement for a producer containing sales summary and payout details."""

    STATUS_PENDING = "pending"
    STATUS_CALCULATED = "calculated"
    STATUS_APPROVED = "approved"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CALCULATED, "Calculated"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_settlements",
        limit_choices_to={"is_producer": True},
    )

    week_start = models.DateField()
    week_end = models.DateField()

    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0500"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payout_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Payment tracking
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_provider = models.CharField(max_length=50, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Approval tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_settlements",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Detailed calculation data stored as JSON for transparency
    calculation_data = models.JSONField(default=dict, blank=True)

    # Failure tracking
    failure_reason = models.TextField(blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start", "-created_at"]
        indexes = [
            models.Index(fields=["producer", "week_start"]),
            models.Index(fields=["status"]),
            models.Index(fields=["week_start", "week_end"]),
        ]

    def __str__(self):
        return f"Settlement {self.id} - {self.producer.username} ({self.week_start} to {self.week_end})"

    def calculate_amounts(self):
        """Recalculate commission and payout amounts based on total sales."""
        self.commission_amount = (self.total_sales * self.commission_rate).quantize(Decimal("0.01"))
        self.payout_amount = (self.total_sales - self.commission_amount).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.calculate_amounts()
        super().save(*args, **kwargs)


class SettlementOrderItem(models.Model):
    """Audit trail - individual order items included in a settlement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement = models.ForeignKey(
        ProducerWeeklySettlement,
        on_delete=models.CASCADE,
        related_name="order_items",
    )

    # Denormalized fields for audit trail (preserved even if original data changes)
    order_id = models.PositiveIntegerField()
    order_item_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2)
    payout = models.DecimalField(max_digits=10, decimal_places=2)

    # Link to original order item (for reference)
    original_order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlement_items",
    )

    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["settlement", "order_id"]),
        ]

    def __str__(self):
        return f"Settlement Item {self.product_name} - {self.settlement.id}"

    def save(self, *args, **kwargs):
        # Auto-calculate commission and payout
        commission_rate = self.settlement.commission_rate if self.settlement else Decimal("0.05")
        self.commission = (self.subtotal * commission_rate).quantize(Decimal("0.01"))
        self.payout = (self.subtotal - self.commission).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class SettlementAuditLog(models.Model):
    """Complete audit trail of all settlement actions."""

    ACTION_CALCULATED = "calculated"
    ACTION_APPROVED = "approved"
    ACTION_PAID = "paid"
    ACTION_FAILED = "failed"
    ACTION_RETRY = "retry"
    ACTION_EXPORTED = "exported"

    ACTION_CHOICES = [
        (ACTION_CALCULATED, "Calculated"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_PAID, "Paid"),
        (ACTION_FAILED, "Failed"),
        (ACTION_RETRY, "Retry"),
        (ACTION_EXPORTED, "Exported"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement = models.ForeignKey(
        ProducerWeeklySettlement,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlement_actions",
    )

    old_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, blank=True, default="")

    notes = models.TextField(blank=True, default="")

    # Metadata for payment details, errors, etc.
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["settlement", "action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - Settlement {self.settlement.id} at {self.created_at}"


class PaymentTransaction(models.Model):
    """Tracks each Stripe Checkout payment with commission breakdown.

    Stores the financial audit trail for every customer payment:
    - total_amount: What the customer paid
    - network_commission: 5% kept by the BRFN platform
    - producer_payout: 95% distributed to producers
    """

    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment_transaction",
        null=True,
        blank=True,
        help_text="Linked after Stripe confirms payment",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )

    # Stripe tracking fields
    stripe_session_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default="")

    # Financial breakdown
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    network_commission = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="5% platform fee",
    )
    producer_payout = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="95% to producers",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    delivery_date = models.DateField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)

    # Per-producer breakdown stored as JSON for transparency
    # Format: [{"producer_id": 1, "username": "farm_a", "subtotal": "100.00", "commission": "5.00", "payout": "95.00"}, ...]
    producer_breakdown = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stripe_session_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["customer", "-created_at"]),
        ]

    def __str__(self):
        return f"Payment {self.id} — ${self.total_amount} ({self.status})"

