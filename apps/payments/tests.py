from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils.timezone import now

from apps.orders.models import Order, OrderItem
from apps.payments.models import (
    PaymentTransaction,
    ProducerWeeklySettlement,
    SettlementAuditLog,
)
from apps.payments.services import SettlementService

pytestmark = pytest.mark.django_db


def test_tc007_payment_transaction_records_single_order_commission(
    customer_user, producer_user, order
):
    payment = PaymentTransaction.objects.create(
        order=order,
        customer=customer_user,
        stripe_session_id="cs_single_order",
        stripe_payment_intent_id="pi_single_order",
        total_amount=order.total_price,
        network_commission=order.total_price * Decimal("0.05"),
        producer_payout=order.total_price * Decimal("0.95"),
        status=PaymentTransaction.STATUS_SUCCEEDED,
        producer_breakdown=[
            {
                "producer_id": producer_user.id,
                "subtotal": str(order.total_price),
                "commission": str(order.total_price * Decimal("0.05")),
                "payout": str(order.total_price * Decimal("0.95")),
            }
        ],
    )

    assert payment.network_commission == Decimal("2.5000")
    assert payment.producer_payout == Decimal("47.5000")
    assert payment.producer_breakdown[0]["producer_id"] == producer_user.id


def test_tc008_payment_breakdown_splits_multi_vendor_order_commission(
    customer_user, producer_user, multiple_producers
):
    second_producer = multiple_producers[0]
    parent_order = Order.objects.create(
        customer=customer_user,
        status=Order.PENDING,
        total_price=Decimal("120.00"),
    )
    payment = PaymentTransaction.objects.create(
        order=parent_order,
        customer=customer_user,
        stripe_session_id="cs_multi_vendor",
        total_amount=Decimal("120.00"),
        network_commission=Decimal("6.00"),
        producer_payout=Decimal("114.00"),
        status=PaymentTransaction.STATUS_SUCCEEDED,
        producer_breakdown=[
            {
                "producer_id": producer_user.id,
                "subtotal": "70.00",
                "commission": "3.50",
                "payout": "66.50",
            },
            {
                "producer_id": second_producer.id,
                "subtotal": "50.00",
                "commission": "2.50",
                "payout": "47.50",
            },
        ],
    )

    assert payment.network_commission == Decimal("6.00")
    assert payment.producer_payout == Decimal("114.00")
    assert sum(
        Decimal(row["commission"]) for row in payment.producer_breakdown
    ) == Decimal("6.00")


def test_tc012_producer_receives_weekly_settlement_for_delivered_orders(
    customer_user, producer_user, product, admin_user
):
    week_start = now().date() - timedelta(days=now().date().weekday())
    week_end = week_start + timedelta(days=6)
    delivered_at = now()
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.DELIVERED,
        total_price=Decimal("50.00"),
        delivered_at=delivered_at,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=2,
        unit_price=Decimal("25.00"),
    )

    settlement = SettlementService.create_settlement(
        producer=producer_user,
        week_start=week_start,
        week_end=week_end,
        performed_by=admin_user,
    )

    assert settlement is not None
    assert settlement.status == ProducerWeeklySettlement.STATUS_CALCULATED
    assert settlement.total_sales == Decimal("50.00")
    assert settlement.commission_amount == Decimal("2.50")
    assert settlement.payout_amount == Decimal("47.50")
    assert settlement.order_items.count() == 1


def test_tc025_admin_can_monitor_commission_calculations_and_audit_actions(
    producer_user, admin_user
):
    settlement = ProducerWeeklySettlement.objects.create(
        producer=producer_user,
        week_start=now().date() - timedelta(days=7),
        week_end=now().date() - timedelta(days=1),
        total_sales=Decimal("200.00"),
        commission_rate=Decimal("0.0500"),
        status=ProducerWeeklySettlement.STATUS_CALCULATED,
    )

    approved = SettlementService.approve_settlement(
        settlement,
        approved_by=admin_user,
        notes="Commission checked",
    )

    assert approved.commission_amount == Decimal("10.00")
    assert approved.payout_amount == Decimal("190.00")
    assert approved.status == ProducerWeeklySettlement.STATUS_APPROVED
    assert SettlementAuditLog.objects.filter(
        settlement=settlement,
        action=SettlementAuditLog.ACTION_APPROVED,
        performed_by=admin_user,
    ).exists()
