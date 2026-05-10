import stripe
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from apps.orders.models import Order, OrderItem, RefundRequest, OrderStatusLog
from apps.payments.models import PaymentTransaction

stripe.api_key = settings.STRIPE_SECRET_KEY

class RefundServiceError(Exception):
    pass

class RefundService:
    @staticmethod
    def calculate_refund_amount(order: Order, order_item: OrderItem = None, reason_category: str = None) -> Decimal:
        """
        Calculate the exact refund amount based on the business rules.
        - Not delivered / Cancel before delivery: Full amount - 1% fee (min $1).
        - Fresh Return (within 2 days): 50% amount - 1% fee (min $1).
        - Spoiled (partial or 100%): Full amount of the item/order. No fee.
        """
        target_amount = order_item.subtotal if order_item else order.total_price
        
        if reason_category in [RefundRequest.REASON_SPOILED, RefundRequest.REASON_OTHER]:
            return target_amount.quantize(Decimal("0.01"))
            
        fee = (target_amount * Decimal("0.01")).quantize(Decimal("0.01"))
        if fee < Decimal("1.00"):
            fee = Decimal("1.00")
            
        if reason_category == RefundRequest.REASON_NOT_DELIVERED:
            refund = target_amount - fee
        elif reason_category == RefundRequest.REASON_FRESH_RETURN:
            refund = (target_amount * Decimal("0.50")).quantize(Decimal("0.01")) - fee
        else:
            refund = target_amount
            
        return max(Decimal("0.00"), refund)

    @staticmethod
    @transaction.atomic
    def process_refund_approval(refund_request: RefundRequest, admin_user, admin_note: str = ""):
        """
        Process the approved refund:
        1. Call Stripe API to refund the money to the customer.
        2. Adjust PaymentTransaction to deduct the refunded amount from producer payout and network commission.
        3. Update Order and RefundRequest status.
        """
        if refund_request.status != RefundRequest.STATUS_PENDING:
            raise RefundServiceError("Refund request is not pending.")

        order = refund_request.order
        # Find the master order to get the Stripe PaymentIntent
        master_order = order.parent_order if order.parent_order else order
        payment_txn = master_order.payment_transaction

        if not payment_txn or payment_txn.status != PaymentTransaction.STATUS_SUCCEEDED:
            raise RefundServiceError("No successful payment transaction found for this order.")

        if not payment_txn.stripe_payment_intent_id:
            raise RefundServiceError("Missing Stripe Payment Intent ID.")

        # 1. Call Stripe to refund
        amount_to_refund = refund_request.requested_amount
        stripe_amount = int(amount_to_refund * 100) # Convert to cents

        try:
            if stripe_amount > 0:
                stripe.Refund.create(
                    payment_intent=payment_txn.stripe_payment_intent_id,
                    amount=stripe_amount,
                    reason="requested_by_customer"
                )
        except stripe.error.StripeError as e:
            raise RefundServiceError(f"Stripe Refund Failed: {str(e)}")

        # 2. Adjust PaymentTransaction
        # The exact amount the item was originally sold for
        original_value = refund_request.order_item.subtotal if refund_request.order_item else order.total_price
        
        # Deduct based on the *original value* of the returned item/order,
        # because the producer doesn't get paid for returned/spoiled items.
        deduct_commission = (original_value * Decimal("0.05")).quantize(Decimal("0.01"))
        deduct_payout = (original_value - deduct_commission).quantize(Decimal("0.01"))
        
        payment_txn.total_amount -= original_value
        payment_txn.network_commission -= deduct_commission
        payment_txn.producer_payout -= deduct_payout
        
        # Adjust producer_breakdown JSON for each affected producer
        if refund_request.order_item:
            # Partial refund: only one producer affected
            affected_producers = {refund_request.order_item.producer.id: refund_request.order_item.subtotal}
        elif order.sub_orders.exists():
            # Master Order refund: deduct each sub-order's value from its producer
            affected_producers = {}
            for sub in order.sub_orders.select_related('producer').all():
                if sub.producer_id:
                    affected_producers[sub.producer_id] = sub.total_price
        elif order.producer_id:
            # Single-producer sub-order
            affected_producers = {order.producer_id: original_value}
        else:
            affected_producers = {}

        for pid, value in affected_producers.items():
            p_commission = (value * Decimal("0.05")).quantize(Decimal("0.01"))
            p_payout = (value - p_commission).quantize(Decimal("0.01"))
            for breakdown in payment_txn.producer_breakdown:
                if breakdown.get("producer_id") == pid:
                    breakdown["subtotal"] = str(max(Decimal("0.00"), Decimal(breakdown["subtotal"]) - value))
                    breakdown["commission"] = str(max(Decimal("0.00"), Decimal(breakdown["commission"]) - p_commission))
                    breakdown["payout"] = str(max(Decimal("0.00"), Decimal(breakdown["payout"]) - p_payout))
                    break

        payment_txn.save()

        # 3. Update Order and RefundRequest status
        refund_request.status = RefundRequest.STATUS_APPROVED
        refund_request.admin_note = admin_note
        from django.utils.timezone import now
        refund_request.resolved_at = now()
        refund_request.save()

        # Update order status
        old_status = order.status
        order.status = Order.REFUNDED
        order.save()

        OrderStatusLog.objects.create(
            order=order,
            old_status=old_status,
            new_status=Order.REFUNDED,
            changed_by=admin_user,
            note=f"Refund approved. Amount: ${amount_to_refund}. Note: {admin_note}"
        )
        
        # Sync sub-orders
        for sub_order in order.sub_orders.all():
            sub_order.status = Order.REFUNDED
            sub_order.save()
            OrderStatusLog.objects.create(
                order=sub_order,
                old_status=old_status,
                new_status=Order.REFUNDED,
                changed_by=admin_user,
                note=f"Refund approved for Master Order. Note: {admin_note}"
            )

        # 4. Restock products if order was cancelled before delivery or returned fresh
        if refund_request.reason_category in [RefundRequest.REASON_NOT_DELIVERED, RefundRequest.REASON_FRESH_RETURN]:
            if refund_request.order_item:
                items_to_restock = [refund_request.order_item]
            elif order.sub_orders.exists():
                # Master Order: items live inside sub-orders, not on the master itself
                items_to_restock = OrderItem.objects.filter(order__parent_order=order)
            else:
                items_to_restock = order.items.all()
            for item in items_to_restock:
                if item and item.product:
                    item.product.stock_quantity += item.quantity
                    item.product.save()

        return refund_request

    @staticmethod
    def reject_refund(refund_request: RefundRequest, admin_user, admin_note: str = ""):
        if refund_request.status != RefundRequest.STATUS_PENDING:
            raise RefundServiceError("Refund request is not pending.")

        refund_request.status = RefundRequest.STATUS_REJECTED
        refund_request.admin_note = admin_note
        from django.utils.timezone import now
        refund_request.resolved_at = now()
        refund_request.save()

        old_status = refund_request.order.status
        # Revert order to the status it had *before* REFUND_REQUESTED by querying audit log
        previous_log = OrderStatusLog.objects.filter(
            order=refund_request.order,
            new_status=Order.REFUND_REQUESTED
        ).order_by('-timestamp').first()
        if previous_log and previous_log.old_status:
            target_status = previous_log.old_status
        else:
            # Fallback: guess from delivered_at
            target_status = Order.DELIVERED if refund_request.order.delivered_at else Order.CONFIRMED
        
        refund_request.order.status = target_status
        refund_request.order.save()

        OrderStatusLog.objects.create(
            order=refund_request.order,
            old_status=old_status,
            new_status=target_status,
            changed_by=admin_user,
            note=f"Refund rejected. Note: {admin_note}"
        )
        
        # Sync sub-orders
        for sub_order in refund_request.order.sub_orders.all():
            sub_order.status = target_status
            sub_order.save()
            OrderStatusLog.objects.create(
                order=sub_order,
                old_status=old_status,
                new_status=target_status,
                changed_by=admin_user,
                note=f"Refund rejected for Master Order. Note: {admin_note}"
            )

        return refund_request
