from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.db import transaction
from django.utils.timezone import now, make_aware
from django.contrib.auth import get_user_model

from apps.orders.models import OrderItem, Order
from apps.accounts.models import ProducerProfile
from .models import (
    ProducerWeeklySettlement,
    SettlementOrderItem,
    SettlementAuditLog,
)


User = get_user_model()


class SettlementCalculationError(Exception):
    """Raised when settlement calculation fails."""
    pass


class SettlementService:
    """Service for calculating and managing weekly producer settlements."""

    COMMISSION_RATE = Decimal("0.05")

    @staticmethod
    def get_week_boundaries(target_date: Optional[datetime] = None) -> Tuple[datetime.date, datetime.date]:
        """
        Get the start (Monday) and end (Sunday) dates of the week containing target_date.
        If target_date is None, uses the previous week.
        """
        if target_date is None:
            target_date = now() - timedelta(days=7)

        # Find Monday of the week (weekday() returns 0 for Monday, 6 for Sunday)
        days_since_monday = target_date.weekday()
        # Handle both datetime and date objects
        the_date = target_date.date() if hasattr(target_date, 'date') and callable(target_date.date) else target_date
        week_start = the_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)

        return week_start, week_end

    @classmethod
    def calculate_producer_settlement(
        cls,
        producer: User,
        week_start: datetime.date,
        week_end: datetime.date,
        dry_run: bool = False
    ) -> Dict:
        """
        Calculate settlement for a single producer for a given week.

        Returns:
            Dict with settlement data and order items.
        """
        # Find all delivered orders for this producer in the date range
        order_items = OrderItem.objects.filter(
            producer=producer,
            order__status=Order.DELIVERED,
            order__delivered_at__date__gte=week_start,
            order__delivered_at__date__lte=week_end,
        ).select_related("order", "product")

        if not order_items.exists():
            return {
                "has_data": False,
                "total_sales": Decimal("0.00"),
                "commission_amount": Decimal("0.00"),
                "payout_amount": Decimal("0.00"),
                "items": [],
            }

        total_sales = Decimal("0.00")
        items_data = []

        for item in order_items:
            subtotal = item.subtotal
            commission = (subtotal * cls.COMMISSION_RATE).quantize(Decimal("0.01"))
            payout = subtotal - commission

            item_data = {
                "order_id": item.order.id,
                "order_item_id": item.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": subtotal,
                "commission": commission,
                "payout": payout,
                "original_order_item": item,
                "delivered_at": item.order.delivered_at,
            }
            items_data.append(item_data)
            total_sales += subtotal

        commission_amount = (total_sales * cls.COMMISSION_RATE).quantize(Decimal("0.01"))
        payout_amount = total_sales - commission_amount

        return {
            "has_data": True,
            "total_sales": total_sales.quantize(Decimal("0.01")),
            "commission_amount": commission_amount,
            "payout_amount": payout_amount,
            "items": items_data,
        }

    @classmethod
    def create_settlement(
        cls,
        producer: User,
        week_start: datetime.date,
        week_end: datetime.date,
        performed_by: Optional[User] = None,
        dry_run: bool = False
    ) -> Optional[ProducerWeeklySettlement]:
        """
        Create a settlement record for a producer.

        Args:
            producer: The producer user
            week_start: Start date of the week
            week_end: End date of the week
            performed_by: User performing the action (for audit log)
            dry_run: If True, don't actually create database records

        Returns:
            ProducerWeeklySettlement instance or None if no sales
        """
        # Check if settlement already exists
        existing = ProducerWeeklySettlement.objects.filter(
            producer=producer,
            week_start=week_start
        ).first()

        if existing:
            raise SettlementCalculationError(
                f"Settlement already exists for {producer.username} for week {week_start}"
            )

        # Calculate settlement data
        data = cls.calculate_producer_settlement(producer, week_start, week_end)

        if not data["has_data"]:
            return None

        if dry_run:
            return None

        with transaction.atomic():
            # Create settlement record
            settlement = ProducerWeeklySettlement.objects.create(
                producer=producer,
                week_start=week_start,
                week_end=week_end,
                total_sales=data["total_sales"],
                commission_rate=cls.COMMISSION_RATE,
                commission_amount=data["commission_amount"],
                payout_amount=data["payout_amount"],
                status=ProducerWeeklySettlement.STATUS_CALCULATED,
                calculation_data={
                    "item_count": len(data["items"]),
                    "calculated_at": now().isoformat(),
                    "calculated_by": performed_by.username if performed_by else "system",
                },
            )

            # Create settlement order items (audit trail)
            for item_data in data["items"]:
                SettlementOrderItem.objects.create(
                    settlement=settlement,
                    order_id=item_data["order_id"],
                    order_item_id=item_data["order_item_id"],
                    product_name=item_data["product_name"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    subtotal=item_data["subtotal"],
                    commission=item_data["commission"],
                    payout=item_data["payout"],
                    original_order_item=item_data["original_order_item"],
                    delivered_at=item_data["delivered_at"],
                )

            # Create audit log
            SettlementAuditLog.objects.create(
                settlement=settlement,
                action=SettlementAuditLog.ACTION_CALCULATED,
                performed_by=performed_by,
                old_status=ProducerWeeklySettlement.STATUS_PENDING,
                new_status=ProducerWeeklySettlement.STATUS_CALCULATED,
                notes=f"Calculated settlement for {len(data['items'])} items",
            )

            return settlement

    @classmethod
    def run_weekly_settlements(
        cls,
        target_date: Optional[datetime] = None,
        dry_run: bool = False,
        performed_by: Optional[User] = None
    ) -> List[Dict]:
        """
        Run settlements for all producers for a given week.

        Args:
            target_date: Date within the week to settle (defaults to last week)
            dry_run: If True, don't create database records
            performed_by: User performing the action

        Returns:
            List of settlement results with status
        """
        week_start, week_end = cls.get_week_boundaries(target_date)

        # Get all producers
        producers = User.objects.filter(is_producer=True)

        results = []

        for producer in producers:
            try:
                settlement = cls.create_settlement(
                    producer=producer,
                    week_start=week_start,
                    week_end=week_end,
                    performed_by=performed_by,
                    dry_run=dry_run,
                )

                if settlement:
                    results.append({
                        "producer": producer.username,
                        "settlement_id": str(settlement.id),
                        "total_sales": str(settlement.total_sales),
                        "payout_amount": str(settlement.payout_amount),
                        "status": "created",
                    })
                else:
                    results.append({
                        "producer": producer.username,
                        "status": "no_sales",
                    })

            except SettlementCalculationError as e:
                results.append({
                    "producer": producer.username,
                    "status": "error",
                    "error": str(e),
                })

        return results

    @classmethod
    def approve_settlement(
        cls,
        settlement: ProducerWeeklySettlement,
        approved_by: User,
        notes: str = ""
    ) -> ProducerWeeklySettlement:
        """Approve a settlement for payment."""
        if settlement.status != ProducerWeeklySettlement.STATUS_CALCULATED:
            raise SettlementCalculationError(
                f"Cannot approve settlement with status: {settlement.status}"
            )

        old_status = settlement.status

        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.approved_by = approved_by
        settlement.approved_at = now()
        settlement.save()

        SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_APPROVED,
            performed_by=approved_by,
            old_status=old_status,
            new_status=settlement.status,
            notes=notes or "Settlement approved for payment",
        )

        return settlement

    @classmethod
    def mark_settlement_paid(
        cls,
        settlement: ProducerWeeklySettlement,
        performed_by: User,
        payment_method: str,
        payment_reference: str,
        payment_provider: str = "",
        notes: str = ""
    ) -> ProducerWeeklySettlement:
        """Mark a settlement as paid."""
        if settlement.status not in [
            ProducerWeeklySettlement.STATUS_APPROVED,
            ProducerWeeklySettlement.STATUS_FAILED,
        ]:
            raise SettlementCalculationError(
                f"Cannot mark settlement as paid with status: {settlement.status}"
            )

        old_status = settlement.status

        settlement.status = ProducerWeeklySettlement.STATUS_PAID
        settlement.payment_method = payment_method
        settlement.payment_reference = payment_reference
        settlement.payment_provider = payment_provider
        settlement.paid_at = now()
        settlement.failure_reason = ""  # Clear any previous failure
        settlement.save()

        SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_PAID,
            performed_by=performed_by,
            old_status=old_status,
            new_status=settlement.status,
            notes=notes or f"Payment processed via {payment_method}",
            metadata={
                "payment_method": payment_method,
                "payment_reference": payment_reference,
                "payment_provider": payment_provider,
                "paid_at": settlement.paid_at.isoformat(),
            },
        )

        return settlement

    @classmethod
    def mark_settlement_failed(
        cls,
        settlement: ProducerWeeklySettlement,
        performed_by: User,
        reason: str,
        retryable: bool = True
    ) -> ProducerWeeklySettlement:
        """Mark a settlement as failed."""
        old_status = settlement.status

        settlement.status = ProducerWeeklySettlement.STATUS_FAILED
        settlement.failure_reason = reason
        if retryable:
            settlement.retry_count += 1
        settlement.save()

        SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_FAILED,
            performed_by=performed_by,
            old_status=old_status,
            new_status=settlement.status,
            notes=reason,
            metadata={
                "retryable": retryable,
                "retry_count": settlement.retry_count,
            },
        )

        return settlement

    @classmethod
    def retry_settlement(
        cls,
        settlement: ProducerWeeklySettlement,
        performed_by: User,
        notes: str = ""
    ) -> ProducerWeeklySettlement:
        """Retry a failed settlement - returns to APPROVED status."""
        if settlement.status != ProducerWeeklySettlement.STATUS_FAILED:
            raise SettlementCalculationError(
                f"Cannot retry settlement with status: {settlement.status}"
            )

        old_status = settlement.status

        settlement.status = ProducerWeeklySettlement.STATUS_APPROVED
        settlement.save()

        SettlementAuditLog.objects.create(
            settlement=settlement,
            action=SettlementAuditLog.ACTION_RETRY,
            performed_by=performed_by,
            old_status=old_status,
            new_status=settlement.status,
            notes=notes or f"Retry attempt #{settlement.retry_count}",
        )

        return settlement
