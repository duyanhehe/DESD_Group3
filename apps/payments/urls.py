from django.urls import path
from .views import (
    # Producer endpoints
    ProducerSettlementListView,
    ProducerSettlementDetailView,
    ProducerSettlementItemsView,
    ProducerSettlementAuditView,
    # Admin endpoints
    AdminSettlementListView,
    AdminSettlementDetailView,
    AdminCalculateSettlementsView,
    AdminApproveSettlementView,
    AdminPaySettlementView,
    AdminFailSettlementView,
    AdminRetrySettlementView,
    AdminSettlementSummaryView,
    AdminSettlementExportView,
)

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # Producer Endpoints
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/settlements/", ProducerSettlementListView.as_view(), name="producer_settlement_list"),
    path("api/v1/settlements/<uuid:settlement_id>/", ProducerSettlementDetailView.as_view(), name="producer_settlement_detail"),
    path("api/v1/settlements/<uuid:settlement_id>/items/", ProducerSettlementItemsView.as_view(), name="producer_settlement_items"),
    path("api/v1/settlements/<uuid:settlement_id>/audit/", ProducerSettlementAuditView.as_view(), name="producer_settlement_audit"),

    # ═══════════════════════════════════════════════════════════════
    # Admin Endpoints
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/admin/settlements/", AdminSettlementListView.as_view(), name="admin_settlement_list"),
    path("api/v1/admin/settlements/calculate/", AdminCalculateSettlementsView.as_view(), name="admin_settlement_calculate"),
    path("api/v1/admin/settlements/summary/", AdminSettlementSummaryView.as_view(), name="admin_settlement_summary"),
    path("api/v1/admin/settlements/export/", AdminSettlementExportView.as_view(), name="admin_settlement_export"),
    path("api/v1/admin/settlements/<uuid:settlement_id>/", AdminSettlementDetailView.as_view(), name="admin_settlement_detail"),
    path("api/v1/admin/settlements/<uuid:settlement_id>/approve/", AdminApproveSettlementView.as_view(), name="admin_settlement_approve"),
    path("api/v1/admin/settlements/<uuid:settlement_id>/pay/", AdminPaySettlementView.as_view(), name="admin_settlement_pay"),
    path("api/v1/admin/settlements/<uuid:settlement_id>/fail/", AdminFailSettlementView.as_view(), name="admin_settlement_fail"),
    path("api/v1/admin/settlements/<uuid:settlement_id>/retry/", AdminRetrySettlementView.as_view(), name="admin_settlement_retry"),
]
