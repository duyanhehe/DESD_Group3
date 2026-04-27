from rest_framework import serializers
from .models import ProducerWeeklySettlement, SettlementOrderItem, SettlementAuditLog, PaymentTransaction


class SettlementOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for settlement order items (audit detail)."""

    class Meta:
        model = SettlementOrderItem
        fields = [
            "id",
            "order_id",
            "order_item_id",
            "product_name",
            "quantity",
            "unit_price",
            "subtotal",
            "commission",
            "payout",
            "delivered_at",
            "created_at",
        ]
        read_only_fields = fields


class SettlementAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for settlement audit trail entries."""

    performed_by_name = serializers.CharField(
        source="performed_by.username",
        read_only=True,
        default=None
    )

    class Meta:
        model = SettlementAuditLog
        fields = [
            "id",
            "action",
            "performed_by",
            "performed_by_name",
            "old_status",
            "new_status",
            "notes",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class ProducerWeeklySettlementSerializer(serializers.ModelSerializer):
    """Serializer for producer settlements - producer view."""

    producer_name = serializers.CharField(source="producer.username", read_only=True)
    approved_by_name = serializers.CharField(
        source="approved_by.username",
        read_only=True,
        default=None
    )

    class Meta:
        model = ProducerWeeklySettlement
        fields = [
            "id",
            "producer",
            "producer_name",
            "week_start",
            "week_end",
            "total_sales",
            "commission_rate",
            "commission_amount",
            "payout_amount",
            "status",
            "payment_method",
            "payment_reference",
            "payment_provider",
            "paid_at",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "calculation_data",
            "failure_reason",
            "retry_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProducerWeeklySettlementDetailSerializer(ProducerWeeklySettlementSerializer):
    """Detailed settlement view with line items and audit log."""

    order_items = SettlementOrderItemSerializer(many=True, read_only=True)
    audit_logs = SettlementAuditLogSerializer(many=True, read_only=True)

    class Meta(ProducerWeeklySettlementSerializer.Meta):
        fields = ProducerWeeklySettlementSerializer.Meta.fields + [
            "order_items",
            "audit_logs",
        ]


class SettlementApproveSerializer(serializers.Serializer):
    """Serializer for approving a settlement."""

    notes = serializers.CharField(required=False, allow_blank=True, default="")


class SettlementPaySerializer(serializers.Serializer):
    """Serializer for marking a settlement as paid."""

    payment_method = serializers.ChoiceField(
        choices=[
            ("bank_transfer", "Bank Transfer"),
            ("check", "Check"),
            ("stripe", "Stripe"),
            ("paypal", "PayPal"),
            ("other", "Other"),
        ]
    )
    payment_reference = serializers.CharField(max_length=100)
    payment_provider = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class SettlementFailSerializer(serializers.Serializer):
    """Serializer for marking a settlement as failed."""

    reason = serializers.CharField(required=True)
    retryable = serializers.BooleanField(default=True)


class SettlementRetrySerializer(serializers.Serializer):
    """Serializer for retrying a failed settlement."""

    notes = serializers.CharField(required=False, allow_blank=True, default="")


class SettlementCalculateSerializer(serializers.Serializer):
    """Serializer for triggering settlement calculation."""

    week_date = serializers.DateField(
        required=False,
        help_text="Date within the week to calculate (defaults to last week)"
    )
    dry_run = serializers.BooleanField(
        default=False,
        help_text="If True, don't create database records"
    )


class SettlementSummarySerializer(serializers.Serializer):
    """Serializer for settlement summary statistics."""

    week_start = serializers.DateField()
    week_end = serializers.DateField()
    total_settlements = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payouts = serializers.DecimalField(max_digits=15, decimal_places=2)
    status_breakdown = serializers.DictField()


class CSVExportSerializer(serializers.Serializer):
    """Serializer for CSV export parameters."""

    week_start = serializers.DateField(required=False)
    week_end = serializers.DateField(required=False)
    status = serializers.ChoiceField(
        choices=ProducerWeeklySettlement.STATUS_CHOICES,
        required=False
    )
    producer_id = serializers.IntegerField(required=False)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions with commission breakdown."""

    customer_name = serializers.CharField(source="customer.username", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "order",
            "customer",
            "customer_name",
            "stripe_session_id",
            "stripe_payment_intent_id",
            "total_amount",
            "network_commission",
            "producer_payout",
            "status",
            "producer_breakdown",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
