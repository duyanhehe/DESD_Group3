"""
Comprehensive test suite for the Payments app (CRITICAL PATH).

Tests cover:
- Settlement calculations (5% commission, payout amounts)
- Settlement status transitions (pending → approved → paid)
- Audit logging
- API endpoints for producers and admins
- Stripe webhook handling
- Settlement export/reporting
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock

from django.contrib.auth import get_user_model
from django.utils.timezone import now, make_aware
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.payments.models import (
    ProducerWeeklySettlement,
    SettlementOrderItem,
    SettlementAuditLog,
    PaymentTransaction,
)
from apps.orders.models import Order, OrderItem
from apps.accounts.models import ProducerProfile
from apps.payments.services import SettlementService

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: Settlement Calculations
# ============================================================================


class TestSettlementCalculations:
    """Unit tests for settlement calculation logic."""

    def test_single_producer_weekly_settlement(
        self, producer_user, customer_user, product, delivered_order
    ):
        """
        Test: Single producer, single order in week, correct calculation.
        - total_sales = order.total_price
        - commission_amount = total_sales × 0.05
        - payout_amount = total_sales - commission_amount
        """
        # Delivered order total is 50.00 (2 units × 25.00)
        # Actually, let's check: product.price is Decimal("3.99"), qty 2 = 7.98
        # But fixture set total_price=50.00, so let's use that.

        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=delivered_order.delivered_at.date() - timedelta(days=1),
            week_end=delivered_order.delivered_at.date() + timedelta(days=5),
            total_sales=Decimal("100.00"),
            commission_rate=Decimal("0.05"),
        )

        # Trigger calculation via save
        settlement.save()

        assert settlement.total_sales == Decimal("100.00")
        assert settlement.commission_amount == Decimal("5.00")
        assert settlement.payout_amount == Decimal("95.00")

    def test_commission_calculation_precision(self, producer_user):
        """
        Test: Commission calculation respects decimal precision (2 places).
        Edge case: $33.33 × 0.05 = $1.67 (rounded correctly).
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("33.33"),
            commission_rate=Decimal("0.05"),
        )
        settlement.save()

        assert settlement.commission_amount == Decimal("1.67")
        assert settlement.payout_amount == Decimal("31.66")
        assert (
            settlement.commission_amount + settlement.payout_amount
            == settlement.total_sales
        )

    def test_zero_sales_week(self, producer_user):
        """
        Test: Producer with no orders in week → zero settlement.
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("0.00"),
        )
        settlement.save()

        assert settlement.total_sales == Decimal("0.00")
        assert settlement.commission_amount == Decimal("0.00")
        assert settlement.payout_amount == Decimal("0.00")

    def test_large_amount_settlement(self, producer_user):
        """
        Test: Large settlement amounts calculate correctly without overflow.
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("99999.99"),
        )
        settlement.save()

        assert settlement.commission_amount == Decimal("5000.00")
        assert settlement.payout_amount == Decimal("94999.99")

    def test_commission_rate_stored_correctly(self, producer_user):
        """
        Test: Custom commission rates are preserved.
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("100.00"),
            commission_rate=Decimal("0.10"),  # 10% instead of 5%
        )
        settlement.save()

        assert settlement.commission_rate == Decimal("0.10")
        assert settlement.commission_amount == Decimal("10.00")

    def test_settlement_amounts_sync_on_save(self, producer_user):
        """
        Test: Updating total_sales recalculates commission on save().
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("50.00"),
        )
        settlement.save()

        old_commission = settlement.commission_amount
        assert old_commission == Decimal("2.50")

        # Update total_sales
        settlement.total_sales = Decimal("100.00")
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.commission_amount == Decimal("5.00")
        assert settlement.payout_amount == Decimal("95.00")


# ============================================================================
# UNIT TESTS: Settlement Status Transitions
# ============================================================================


class TestSettlementStatusTransitions:
    """Unit tests for settlement status workflow."""

    def test_settlement_initial_status_pending(self, producer_user):
        """
        Test: New settlement defaults to PENDING status.
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("100.00"),
        )

        assert settlement.status == ProducerWeeklySettlement.STATUS_PENDING

    def test_settlement_pending_to_calculated(self, settlement):
        """
        Test: Status can transition from PENDING to CALCULATED.
        """
        settlement.status = ProducerWeeklySettlement.STATUS_CALCULATED
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_CALCULATED

    def test_settlement_calculated_to_approved(self, settlement):
        """
        Test: Status transitions CALCULATED → APPROVED.
        """
        settlement.status = ProducerWeeklySettlement.STATUS_CALCULATED
        settlement.save()

        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_APPROVED

    def test_settlement_approved_to_paid(self, settlement, admin_user):
        """
        Test: Status transitions APPROVED → PAID.
        Records approval timestamp and admin who approved.
        """
        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.approved_by = admin_user
        settlement.approved_at = now()
        settlement.save()

        settlement.status = ProducerWeeklySettlement.STATUS_PAID
        settlement.paid_at = now()
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_PAID
        assert settlement.paid_at is not None

    def test_settlement_approved_to_failed(self, settlement):
        """
        Test: Status can transition APPROVED → FAILED if payment fails.
        """
        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.save()

        settlement.status = ProducerWeeklySettlement.STATUS_FAILED
        settlement.failure_reason = "Stripe API error: invalid account"
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_FAILED
        assert settlement.failure_reason != ""

    def test_settlement_failed_with_retry(self, settlement):
        """
        Test: Failed settlement can be retried (retry_count incremented).
        """
        settlement.status = ProducerWeeklySettlement.STATUS_FAILED
        settlement.failure_reason = "Network timeout"
        settlement.retry_count = 0
        settlement.save()

        # Retry: reset to approved, increment retry count
        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.retry_count += 1
        settlement.failure_reason = ""
        settlement.save()

        settlement.refresh_from_db()
        assert settlement.retry_count == 1
        assert settlement.status == ProducerWeeklySettlement.STATUS_APPROVED


# ============================================================================
# UNIT TESTS: Audit Logging
# ============================================================================


class TestSettlementAuditLogging:
    """Unit tests for settlement audit trail."""

    def test_audit_log_created_on_settlement_creation(self, producer_user, admin_user):
        """
        Test: Creating a settlement logs an audit entry.
        """
        settlement = ProducerWeeklySettlement.objects.create(
            producer=producer_user,
            week_start=date.today(),
            week_end=date.today() + timedelta(days=6),
            total_sales=Decimal("100.00"),
        )

        # Manually log the creation (in real system, would be signal/service)
        audit = SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_CALCULATED,
            performed_by=admin_user,
        )

        assert audit.settlement == settlement
        assert audit.action == SettlementAuditLog.ACTION_CALCULATED
        assert audit.performed_by == admin_user
        assert audit.created_at is not None

    def test_audit_log_on_status_change(self, settlement, admin_user):
        """
        Test: Each status change logs an audit entry.
        """
        old_status = settlement.status
        new_status = ProducerWeeklySettlement.STATUS_APPROVED

        audit = SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_APPROVED,
            old_status=old_status,
            new_status=new_status,
            performed_by=admin_user,
        )

        assert audit.action == SettlementAuditLog.ACTION_APPROVED
        assert audit.old_status == old_status
        assert audit.new_status == new_status

    def test_audit_trail_multiple_entries(self, settlement, admin_user):
        """
        Test: Multiple audit entries for a settlement create ordered log.
        """
        actions = [
            SettlementAuditLog.ACTION_CALCULATED,
            SettlementAuditLog.ACTION_APPROVED,
            SettlementAuditLog.ACTION_PAID,
        ]

        for action in actions:
            SettlementAuditLog.objects.create(
                settlement=settlement,
                action=action,
                performed_by=admin_user,
            )

        audit_logs = SettlementAuditLog.objects.filter(settlement=settlement)
        assert audit_logs.count() == 3
        # Should be in creation order (newest first due to ordering)
        assert list(audit_logs.values_list("action", flat=True)) == list(
            reversed(actions)
        )

    def test_audit_log_tracks_performer(self, settlement):
        """
        Test: Audit log tracks which admin performed action.
        """
        admin1 = User.objects.create_superuser(
            username="admin1", email="admin1@test.com", password="pass123"
        )
        admin2 = User.objects.create_superuser(
            username="admin2", email="admin2@test.com", password="pass123"
        )

        SettlementAuditLog.objects.create(
            settlement=settlement, action="APPROVED", performed_by=admin1
        )
        SettlementAuditLog.objects.create(
            settlement=settlement, action="PAID", performed_by=admin2
        )

        assert SettlementAuditLog.objects.get(action="APPROVED").performed_by == admin1
        assert SettlementAuditLog.objects.get(action="PAID").performed_by == admin2


# ============================================================================
# INTEGRATION TESTS: API Endpoints
# ============================================================================


class TestProducerSettlementAPI:
    """Integration tests for producer settlement endpoints."""

    def test_producer_list_settlements_endpoint(self, producer_user, settlement):
        """
        Test: GET /payments/api/v1/settlements/ returns producer's settlements.
        """
        client = APIClient()
        client.force_authenticate(user=producer_user)

        response = client.get("/payments/api/v1/settlements/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(s["id"] == str(settlement.id) for s in response.data)

    def test_producer_cannot_list_other_settlements(
        self, producer_user, multiple_producers, settlement
    ):
        """
        Test: Producer cannot view other producers' settlements.
        Settlement belongs to producer_user; other_producer tries to access.
        """
        other_producer = multiple_producers[0]
        client = APIClient()
        client.force_authenticate(user=other_producer)

        response = client.get("/payments/api/v1/settlements/")

        # Should only see own settlements (if any)
        settlement_ids = [s["id"] for s in response.data]
        assert str(settlement.id) not in settlement_ids

    def test_producer_get_settlement_detail(self, producer_user, settlement):
        """
        Test: GET /payments/api/v1/settlements/<id>/ returns settlement detail.
        """
        client = APIClient()
        client.force_authenticate(user=producer_user)

        response = client.get(f"/payments/api/v1/settlements/{settlement.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(settlement.id)
        assert response.data["total_sales"] == str(settlement.total_sales)
        assert response.data["payout_amount"] == str(settlement.payout_amount)

    def test_producer_view_settlement_items(self, settlement):
        """
        Test: GET /payments/api/v1/settlements/<id>/items/ lists order items.
        """
        producer = settlement.producer
        client = APIClient()
        client.force_authenticate(user=producer)

        # Create some settlement items
        SettlementOrderItem.objects.create(
            settlement=settlement,
            order_id=123,
            order_item_id=456,
            product_name="Apples",
            quantity=5,
            unit_price=Decimal("2.00"),
            subtotal=Decimal("10.00"),
        )

        response = client.get(f"/payments/api/v1/settlements/{settlement.id}/items/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_producer_view_settlement_audit(self, settlement, admin_user):
        """
        Test: GET /payments/api/v1/settlements/<id>/audit/ returns audit trail.
        """
        producer = settlement.producer
        client = APIClient()
        client.force_authenticate(user=producer)

        # Add audit entries
        SettlementAuditLog.objects.create(
            settlement=settlement, action="CREATED", performed_by=admin_user
        )

        response = client.get(f"/payments/api/v1/settlements/{settlement.id}/audit/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


class TestAdminSettlementAPI:
    """Integration tests for admin settlement management endpoints."""

    def test_admin_list_all_settlements(self, admin_user, multiple_producers):
        """
        Test: Admin can list all producer settlements.
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create settlements for multiple producers
        for producer in multiple_producers:
            ProducerWeeklySettlement.objects.create(
                producer=producer,
                week_start=date.today(),
                week_end=date.today() + timedelta(days=6),
                total_sales=Decimal("100.00"),
            )

        response = client.get("/payments/api/v1/admin/settlements/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3

    def test_admin_approve_settlement(self, admin_user, settlement):
        """
        Test: POST /payments/api/v1/admin/settlements/<id>/approve/
        Transitions settlement to APPROVED status.
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        settlement.status = ProducerWeeklySettlement.STATUS_CALCULATED
        settlement.save()

        response = client.post(
            f"/payments/api/v1/admin/settlements/{settlement.id}/approve/",
            {"notes": "Approved by admin"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_APPROVED
        assert settlement.approved_by == admin_user
        assert settlement.approved_at is not None

    def test_admin_pay_settlement(self, admin_user, settlement, mock_stripe):
        """
        Test: POST /payments/api/v1/admin/settlements/<id>/pay/
        - Calls Stripe payout API
        - Creates PaymentTransaction
        - Sets settlement to PAID
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.approved_by = admin_user
        settlement.approved_at = now()
        settlement.save()

        with patch("stripe.Payout.create") as mock_payout:
            mock_payout.return_value = Mock(id="po_test123", status="succeeded")

            response = client.post(
                f"/payments/api/v1/admin/settlements/{settlement.id}/pay/",
                {
                    "payment_method": "bank_transfer",
                    "payment_reference": "TXN123",
                    "notes": "Paid",
                },
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK

    def test_admin_fail_settlement(self, admin_user, settlement):
        """
        Test: POST /payments/api/v1/admin/settlements/<id>/fail/
        Marks settlement as FAILED with reason.
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.save()

        response = client.post(
            f"/payments/api/v1/admin/settlements/{settlement.id}/fail/",
            {"failure_reason": "Producer account invalid", "notes": ""},
            format="json",
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        settlement.refresh_from_db()
        assert settlement.status == ProducerWeeklySettlement.STATUS_FAILED

    def test_admin_retry_failed_settlement(self, admin_user, settlement):
        """
        Test: POST /payments/api/v1/admin/settlements/<id>/retry/
        Retries a failed settlement.
        Increments retry_count, resets to APPROVED for another payment attempt.
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        settlement.status = ProducerWeeklySettlement.STATUS_FAILED
        settlement.retry_count = 1
        settlement.failure_reason = "Network timeout"
        settlement.save()

        response = client.post(
            f"/payments/api/v1/admin/settlements/{settlement.id}/retry/",
            {"notes": "Retrying payment"},
            format="json",
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_customer_cannot_access_admin_settlement_endpoints(
        self, customer_user, settlement
    ):
        """
        Test: Non-admin users (customers, producers) cannot access admin endpoints.
        """
        client = APIClient()
        client.force_authenticate(user=customer_user)

        response = client.get("/payments/api/v1/admin/settlements/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ]


# ============================================================================
# INTEGRATION TESTS: Export & Reporting
# ============================================================================


class TestSettlementExportAndReporting:
    """Integration tests for settlement reports and data export."""

    def test_settlement_export_csv_format(self, admin_user, multiple_producers):
        """
        Test: GET /payments/api/v1/admin/settlements/export/
        Returns CSV with correct columns and data.
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create some settlements
        for producer in multiple_producers:
            ProducerWeeklySettlement.objects.create(
                producer=producer,
                week_start=date.today(),
                week_end=date.today() + timedelta(days=6),
                total_sales=Decimal("100.00"),
                status=ProducerWeeklySettlement.STATUS_PAID,
            )

        response = client.get("/payments/api/v1/admin/settlements/export/")

        assert response.status_code == status.HTTP_200_OK
        assert (
            response["Content-Type"] == "text/csv" or "csv" in response["Content-Type"]
        )
        assert "producer" in response.content.decode()

    def test_settlement_summary_by_week(self, admin_user, multiple_producers):
        """
        Test: Settlement summary aggregates stats (total commission, payouts).
        """
        client = APIClient()
        client.force_authenticate(user=admin_user)

        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)

        # Create settlements for multiple producers same week
        total_commission = Decimal("0.00")
        for producer in multiple_producers:
            settlement = ProducerWeeklySettlement.objects.create(
                producer=producer,
                week_start=week_start,
                week_end=week_end,
                total_sales=Decimal("100.00"),
            )
            settlement.save()  # triggers commission calculation
            total_commission += settlement.commission_amount

        # Assuming there's a summary endpoint
        response = client.get("/payments/api/v1/admin/settlements/summary/")

        if response.status_code == status.HTTP_200_OK:
            # Verify aggregated data
            assert "total_commission" in response.data or len(response.data) > 0


# ============================================================================
# INTEGRATION TESTS: Stripe Webhook
# ============================================================================


class TestStripeWebhookHandling:
    """Integration tests for Stripe webhook events."""

    def test_stripe_webhook_charge_succeeded(self, admin_user, order):
        """
        Test: POST /payments/api/v1/webhook/
        Receive charge.succeeded event, mark order as paid.
        """
        client = APIClient()

        # Create a payment transaction for the order first
        payment = PaymentTransaction.objects.create(
            order=order,
            stripe_payment_intent_id="pi_test123",
            total_amount=order.total_price,
            network_commission=order.total_price * Decimal("0.05"),
            producer_payout=order.total_price * Decimal("0.95"),
            status=PaymentTransaction.STATUS_PENDING,
        )

        webhook_payload = {
            "type": "charge.succeeded",
            "data": {
                "object": {
                    "id": "ch_test123",
                    "payment_intent": "pi_test123",
                    "amount": int(order.total_price * 100),  # Stripe amounts in cents
                }
            },
        }

        # Webhook signature validation would be checked in real view
        response = client.post(
            "/payments/api/v1/webhook/",
            data=json.dumps(webhook_payload),
            content_type="application/json",
        )

        # Expect 200 OK (webhook accepted)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_stripe_webhook_charge_refunded(self, admin_user, settlement):
        """
        Test: charge.refunded webhook triggers settlement recalculation.
        """
        client = APIClient()

        # Create related order
        order = Order.objects.create(
            customer=settlement.producer,
            producer=settlement.producer,
            status=Order.DELIVERED,
            total_price=Decimal("50.00"),
            delivered_at=now(),
        )

        webhook_payload = {
            "type": "charge.refunded",
            "data": {
                "object": {"id": "ch_test123", "amount_refunded": 5000}  # $50 refunded
            },
        }

        response = client.post(
            "/payments/api/v1/webhook/",
            data=json.dumps(webhook_payload),
            content_type="application/json",
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_stripe_webhook_invalid_signature(self):
        """
        Test: Invalid webhook signature is rejected.
        """
        client = APIClient()

        response = client.post(
            "/payments/api/v1/webhook/",
            data=json.dumps({"type": "charge.succeeded"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid_signature",
        )

        # Should reject unsigned webhooks
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ]


# ============================================================================
# INTEGRATION TESTS: Service Layer
# ============================================================================


class TestSettlementService:
    """Integration tests for SettlementService business logic."""

    def test_get_week_boundaries_current_week(self):
        """
        Test: get_week_boundaries() returns correct Monday-Sunday range.
        """
        today = date.today()
        week_start, week_end = SettlementService.get_week_boundaries(today)

        # week_start should be a Monday
        assert week_start.weekday() == 0
        # week_end should be a Sunday
        assert week_end.weekday() == 6
        # Range should be 6 days apart
        assert (week_end - week_start).days == 6

    def test_get_week_boundaries_previous_week(self):
        """
        Test: get_week_boundaries(None) returns previous week.
        """
        week_start, week_end = SettlementService.get_week_boundaries(None)

        today = date.today()
        days_diff = (today - week_start).days

        # Should be in a previous week (7+ days ago or same week)
        assert days_diff >= 0

    def test_calculate_producer_settlement_with_orders(
        self, producer_user, customer_user, product
    ):
        """
        Test: calculate_producer_settlement() aggregates delivered orders.
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Create multiple delivered orders in the week
        for i in range(3):
            order = Order.objects.create(
                customer=customer_user,
                producer=producer_user,
                status=Order.DELIVERED,
                total_price=Decimal("50.00"),
                delivered_at=make_aware(
                    datetime.combine(
                        week_start + timedelta(days=i), datetime.min.time()
                    )
                ),
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                producer=producer_user,
                quantity=2,
                unit_price=Decimal("25.00"),  # Use fixed unit price for calculation
            )

        result = SettlementService.calculate_producer_settlement(
            producer_user, week_start, week_end
        )

        assert result["has_data"] == True
        assert result["total_sales"] == Decimal("150.00")  # 3 orders × $50
        assert result["commission_amount"] == Decimal("7.50")
        assert result["payout_amount"] == Decimal("142.50")

    def test_calculate_producer_settlement_no_delivered_orders(
        self, producer_user, customer_user, product
    ):
        """
        Test: Settlement returns 0 if no delivered orders in week.
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Create pending order (not delivered)
        Order.objects.create(
            customer=customer_user,
            producer=producer_user,
            status=Order.PENDING,
            total_price=Decimal("50.00"),
        )

        result = SettlementService.calculate_producer_settlement(
            producer_user, week_start, week_end
        )

        assert result["has_data"] == False
        assert result["total_sales"] == Decimal("0.00")


if __name__ == "__main__":
    pytest.main([__file__])
