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
        
        # Calculate how much producer and platform lose. 
        # Note: If it's a fresh return, we refund 50% minus fee. 
        # The producer still loses the item, so their payout should theoretically be reduced by the full 95% of the original value?
        # The requirements said: "tự động trừ đi số tiền tương ứng trong báo cáo doanh thu của Producer và phần hoa hồng 5% ... giảm đi".
        # We will deduct based on the *original value* of the item returned/spoiled, because the producer doesn't get paid for returned/spoiled items.
        deduct_commission = (original_value * Decimal("0.05")).quantize(Decimal("0.01"))
        deduct_payout = (original_value - deduct_commission).quantize(Decimal("0.01"))
        
        payment_txn.total_amount -= original_value
        payment_txn.network_commission -= deduct_commission
        payment_txn.producer_payout -= deduct_payout
        
        # Also adjust the producer_breakdown JSON
        if refund_request.order_item:
            producer_id = refund_request.order_item.producer.id
        else:
            producer_id = order.producer.id if order.producer else None

        if producer_id:
            for breakdown in payment_txn.producer_breakdown:
                if breakdown.get("producer_id") == producer_id:
                    current_subtotal = Decimal(breakdown["subtotal"])
                    current_subtotal -= original_value
                    breakdown["subtotal"] = str(max(Decimal("0.00"), current_subtotal))
                    breakdown["commission"] = str(max(Decimal("0.00"), Decimal(breakdown["commission"]) - deduct_commission))
                    breakdown["payout"] = str(max(Decimal("0.00"), Decimal(breakdown["payout"]) - deduct_payout))
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
        # Revert order status from REFUND_REQUESTED to previous state based on delivery status
        target_status = Order.DELIVERED if refund_request.order.delivered_at else Order.CONFIRMED # Simplification
        
        refund_request.order.status = target_status
        refund_request.order.save()

        OrderStatusLog.objects.create(
            order=refund_request.order,
            old_status=old_status,
            new_status=target_status,
            changed_by=admin_user,
            note=f"Refund rejected. Note: {admin_note}"
        )

        return refund_request
