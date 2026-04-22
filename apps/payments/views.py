from datetime import datetime, timedelta
from decimal import Decimal
import csv
from io import StringIO

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils.timezone import now
from django.conf import settings
from django.db import transaction
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics

from apps.orders.models import Cart, Order, OrderItem, OrderStatusLog
from .models import ProducerWeeklySettlement, SettlementOrderItem, SettlementAuditLog
from .serializers import (
    ProducerWeeklySettlementSerializer,
    ProducerWeeklySettlementDetailSerializer,
    SettlementOrderItemSerializer,
    SettlementAuditLogSerializer,
    SettlementApproveSerializer,
    SettlementPaySerializer,
    SettlementFailSerializer,
    SettlementRetrySerializer,
    SettlementCalculateSerializer,
    SettlementSummarySerializer,
    CSVExportSerializer,
)
from .services import SettlementService, SettlementCalculationError


# ═══════════════════════════════════════════════════════════════
# Producer Endpoints
# ═══════════════════════════════════════════════════════════════

class ProducerSettlementListView(APIView):
    """GET — List all settlements for the logged-in producer."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access settlements."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlements = ProducerWeeklySettlement.objects.filter(
            producer=request.user
        ).order_by("-week_start")

        serializer = ProducerWeeklySettlementSerializer(settlements, many=True)
        return Response(serializer.data)


class ProducerSettlementDetailView(APIView):
    """GET — Detailed settlement with line items and audit trail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, settlement_id):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access settlements."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(
            ProducerWeeklySettlement,
            id=settlement_id,
            producer=request.user
        )

        serializer = ProducerWeeklySettlementDetailSerializer(settlement)
        return Response(serializer.data)


class ProducerSettlementItemsView(APIView):
    """GET — Line items breakdown for a settlement."""

    permission_classes = [IsAuthenticated]

    def get(self, request, settlement_id):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access settlements."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(
            ProducerWeeklySettlement,
            id=settlement_id,
            producer=request.user
        )

        items = settlement.order_items.all()
        serializer = SettlementOrderItemSerializer(items, many=True)
        return Response(serializer.data)


class ProducerSettlementAuditView(APIView):
    """GET — Audit trail for a settlement."""

    permission_classes = [IsAuthenticated]

    def get(self, request, settlement_id):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access settlements."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(
            ProducerWeeklySettlement,
            id=settlement_id,
            producer=request.user
        )

        audit_logs = settlement.audit_logs.all()
        serializer = SettlementAuditLogSerializer(audit_logs, many=True)
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════════
# Admin Endpoints
# ═══════════════════════════════════════════════════════════════

class AdminSettlementListView(APIView):
    """GET — List all settlements with filtering (admin only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlements = ProducerWeeklySettlement.objects.all().order_by("-week_start")

        # Apply filters
        status_filter = request.query_params.get("status")
        producer_id = request.query_params.get("producer_id")
        week_start = request.query_params.get("week_start")
        week_end = request.query_params.get("week_end")

        if status_filter:
            settlements = settlements.filter(status=status_filter)
        if producer_id:
            settlements = settlements.filter(producer_id=producer_id)
        if week_start:
            settlements = settlements.filter(week_start=week_start)
        if week_end:
            settlements = settlements.filter(week_end=week_end)

        serializer = ProducerWeeklySettlementSerializer(settlements, many=True)
        return Response(serializer.data)


class AdminSettlementDetailView(APIView):
    """GET — Admin view of settlement details."""

    permission_classes = [IsAuthenticated]

    def get(self, request, settlement_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(ProducerWeeklySettlement, id=settlement_id)
        serializer = ProducerWeeklySettlementDetailSerializer(settlement)
        return Response(serializer.data)


class AdminCalculateSettlementsView(APIView):
    """POST — Trigger settlement calculation for a week."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SettlementCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        week_date = serializer.validated_data.get("week_date")
        dry_run = serializer.validated_data.get("dry_run", False)

        try:
            results = SettlementService.run_weekly_settlements(
                target_date=week_date,
                dry_run=dry_run,
                performed_by=request.user
            )

            return Response({
                "message": f"Processed {len(results)} producers",
                "dry_run": dry_run,
                "week_start": SettlementService.get_week_boundaries(week_date)[0].isoformat(),
                "week_end": SettlementService.get_week_boundaries(week_date)[1].isoformat(),
                "results": results,
            })

        except SettlementCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminApproveSettlementView(APIView):
    """POST — Approve a settlement for payment."""

    permission_classes = [IsAuthenticated]

    def post(self, request, settlement_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(ProducerWeeklySettlement, id=settlement_id)

        serializer = SettlementApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = SettlementService.approve_settlement(
                settlement=settlement,
                approved_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )

            return Response({
                "message": "Settlement approved successfully",
                "settlement": ProducerWeeklySettlementSerializer(settlement).data,
            })

        except SettlementCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminPaySettlementView(APIView):
    """POST — Mark a settlement as paid."""

    permission_classes = [IsAuthenticated]

    def post(self, request, settlement_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(ProducerWeeklySettlement, id=settlement_id)

        serializer = SettlementPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = SettlementService.mark_settlement_paid(
                settlement=settlement,
                performed_by=request.user,
                payment_method=serializer.validated_data["payment_method"],
                payment_reference=serializer.validated_data["payment_reference"],
                payment_provider=serializer.validated_data.get("payment_provider", ""),
                notes=serializer.validated_data.get("notes", ""),
            )

            return Response({
                "message": "Settlement marked as paid",
                "settlement": ProducerWeeklySettlementSerializer(settlement).data,
            })

        except SettlementCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminFailSettlementView(APIView):
    """POST — Mark a settlement as failed."""

    permission_classes = [IsAuthenticated]

    def post(self, request, settlement_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(ProducerWeeklySettlement, id=settlement_id)

        serializer = SettlementFailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = SettlementService.mark_settlement_failed(
                settlement=settlement,
                performed_by=request.user,
                reason=serializer.validated_data["reason"],
                retryable=serializer.validated_data.get("retryable", True),
            )

            return Response({
                "message": "Settlement marked as failed",
                "settlement": ProducerWeeklySettlementSerializer(settlement).data,
            })

        except SettlementCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminRetrySettlementView(APIView):
    """POST — Retry a failed settlement."""

    permission_classes = [IsAuthenticated]

    def post(self, request, settlement_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        settlement = get_object_or_404(ProducerWeeklySettlement, id=settlement_id)

        serializer = SettlementRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = SettlementService.retry_settlement(
                settlement=settlement,
                performed_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )

            return Response({
                "message": "Settlement ready for retry",
                "settlement": ProducerWeeklySettlementSerializer(settlement).data,
            })

        except SettlementCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminSettlementSummaryView(APIView):
    """GET — Weekly summary statistics for settlements."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        week_start = request.query_params.get("week_start")
        week_end = request.query_params.get("week_end")

        if not week_start or not week_end:
            # Default to current week
            week_start, week_end = SettlementService.get_week_boundaries()
            week_start = week_start.isoformat()
            week_end = week_end.isoformat()

        settlements = ProducerWeeklySettlement.objects.filter(
            week_start=week_start,
            week_end=week_end,
        )

        total_sales = Decimal("0.00")
        total_commission = Decimal("0.00")
        total_payouts = Decimal("0.00")
        status_breakdown = {}

        for settlement in settlements:
            total_sales += settlement.total_sales
            total_commission += settlement.commission_amount
            total_payouts += settlement.payout_amount

            status_breakdown[settlement.status] = status_breakdown.get(settlement.status, 0) + 1

        summary = {
            "week_start": week_start,
            "week_end": week_end,
            "total_settlements": settlements.count(),
            "total_sales": total_sales.quantize(Decimal("0.01")),
            "total_commission": total_commission.quantize(Decimal("0.01")),
            "total_payouts": total_payouts.quantize(Decimal("0.01")),
            "status_breakdown": status_breakdown,
        }

        return Response(summary)


class AdminSettlementExportView(APIView):
    """GET — CSV export of settlements for accounting/tax."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CSVExportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # Build queryset
        settlements = ProducerWeeklySettlement.objects.all().order_by("-week_start")

        if serializer.validated_data.get("week_start"):
            settlements = settlements.filter(week_start=serializer.validated_data["week_start"])
        if serializer.validated_data.get("week_end"):
            settlements = settlements.filter(week_end=serializer.validated_data["week_end"])
        if serializer.validated_data.get("status"):
            settlements = settlements.filter(status=serializer.validated_data["status"])
        if serializer.validated_data.get("producer_id"):
            settlements = settlements.filter(producer_id=serializer.validated_data["producer_id"])

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow([
            "week_start",
            "week_end",
            "producer_id",
            "producer_username",
            "business_name",
            "tax_id",
            "total_sales",
            "commission_rate",
            "commission_amount",
            "payout_amount",
            "status",
            "approved_at",
            "paid_at",
            "payment_method",
            "payment_reference",
        ])

        # Data rows
        for settlement in settlements.select_related("producer", "producer__producer_profile"):
            profile = getattr(settlement.producer, "producer_profile", None)

            writer.writerow([
                settlement.week_start.isoformat(),
                settlement.week_end.isoformat(),
                settlement.producer.id,
                settlement.producer.username,
                profile.business_name if profile else "",
                profile.tax_id if profile else "",
                str(settlement.total_sales),
                str(settlement.commission_rate),
                str(settlement.commission_amount),
                str(settlement.payout_amount),
                settlement.status,
                settlement.approved_at.isoformat() if settlement.approved_at else "",
                settlement.paid_at.isoformat() if settlement.paid_at else "",
                settlement.payment_method or "",
                settlement.payment_reference or "",
            ])

        # Create response
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="settlements_export.csv"'

        return response


# ═══════════════════════════════════════════════════════════════
# Customer Checkout Endpoints (Stripe)
# ═══════════════════════════════════════════════════════════════

class CreateCheckoutSessionView(APIView):
    """POST — Create a Stripe checkout session from the customer's cart."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(customer=request.user)
            cart_items = cart.items.select_related("product").all()
        except Cart.DoesNotExist:
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Build Stripe line items
        line_items = []
        for item in cart_items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item.product.name,
                    },
                    "unit_amount": int(item.product.price * 100),  # Stripe uses cents
                },
                "quantity": item.quantity,
            })

        try:
            # Create a Stripe Checkout Session
            frontend_url = request.build_absolute_uri('/')[:-1] # e.g. http://localhost:8000
            
            if settings.STRIPE_SECRET_KEY == "sk_test_mock":
                StripeWebhookView()._fulfill_order(request.user.id, "mock_session_123")
                return Response({"checkout_url": frontend_url + "/?order=success"})
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=frontend_url + '/?order=success',
                cancel_url=frontend_url + '/cart/?order=cancel',
                client_reference_id=str(request.user.id),
                metadata={
                    "user_id": request.user.id
                }
            )
            return Response({'checkout_url': checkout_session.url})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(APIView):
    """POST — Handle Stripe webhooks (e.g., checkout.session.completed)."""

    permission_classes = []  # Stripe doesn't send auth headers

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Handle the checkout.session.completed event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            user_id = session.get('client_reference_id')
            if user_id:
                self.fulfill_order(user_id)

        return Response(status=status.HTTP_200_OK)

    def fulfill_order(self, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            cart = Cart.objects.get(customer=user)
            cart_items = cart.items.select_related("product").all()
            
            if not cart_items.exists():
                return
                
            with transaction.atomic():
                # 1. Create Master Order
                total = sum(item.product.price * item.quantity for item in cart_items)
                
                master_order = Order.objects.create(
                    customer=user,
                    status=Order.CONFIRMED, # Paid via Stripe
                    total_price=total,
                )
                
                OrderStatusLog.objects.create(
                    order=master_order,
                    old_status="",
                    new_status=Order.CONFIRMED,
                    note="Paid via Stripe Checkout",
                )
                
                # Group items by producer
                items_by_producer = {}
                for item in cart_items:
                    producer = item.product.producer
                    if producer not in items_by_producer:
                        items_by_producer[producer] = []
                    items_by_producer[producer].append(item)
                
                # 2. Create Sub-Orders
                for producer, items in items_by_producer.items():
                    sub_total = sum(i.product.price * i.quantity for i in items)
                    sub_order = Order.objects.create(
                        customer=user,
                        parent_order=master_order,
                        producer=producer,
                        status=Order.CONFIRMED,
                        total_price=sub_total,
                    )
                    
                    OrderStatusLog.objects.create(
                        order=sub_order,
                        old_status="",
                        new_status=Order.CONFIRMED,
                        note="Sub-order created from Master Order",
                    )
                    
                    for item in items:
                        OrderItem.objects.create(
                            order=sub_order,
                            product=item.product,
                            producer=producer,
                            quantity=item.quantity,
                            unit_price=item.product.price,
                        )
                        # deduct stock
                        item.product.stock_quantity -= item.quantity
                        item.product.save()

                # 3. Clear cart
                cart.items.all().delete()
                
        except Exception as e:
            # In production, log this error securely
            print(f"Error fulfilling order: {str(e)}")
