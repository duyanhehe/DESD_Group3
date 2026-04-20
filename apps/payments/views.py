from datetime import datetime, timedelta
from decimal import Decimal
import csv
from io import StringIO

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics

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

