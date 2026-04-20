from django.contrib import admin
from .models import ProducerWeeklySettlement, SettlementOrderItem, SettlementAuditLog


class SettlementOrderItemInline(admin.TabularInline):
    model = SettlementOrderItem
    extra = 0
    readonly_fields = [
        "order_id", "order_item_id", "product_name", "quantity",
        "unit_price", "subtotal", "commission", "payout", "delivered_at"
    ]
    can_delete = False


class SettlementAuditLogInline(admin.TabularInline):
    model = SettlementAuditLog
    extra = 0
    readonly_fields = [
        "action", "performed_by", "old_status", "new_status",
        "notes", "metadata", "created_at"
    ]
    can_delete = False


@admin.register(ProducerWeeklySettlement)
class ProducerWeeklySettlementAdmin(admin.ModelAdmin):
    list_display = [
        "id", "producer", "week_start", "week_end", "total_sales",
        "payout_amount", "status", "approved_at", "paid_at"
    ]
    list_filter = ["status", "week_start", "payment_method"]
    search_fields = ["producer__username", "payment_reference"]
    readonly_fields = [
        "id", "total_sales", "commission_amount", "payout_amount",
        "created_at", "updated_at"
    ]
    inlines = [SettlementOrderItemInline, SettlementAuditLogInline]
    date_hierarchy = "week_start"


@admin.register(SettlementOrderItem)
class SettlementOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id", "settlement", "product_name", "quantity",
        "subtotal", "commission", "payout"
    ]
    list_filter = ["settlement__week_start"]
    search_fields = ["product_name", "settlement__producer__username"]
    readonly_fields = ["commission", "payout"]


@admin.register(SettlementAuditLog)
class SettlementAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "id", "settlement", "action", "performed_by",
        "old_status", "new_status", "created_at"
    ]
    list_filter = ["action", "created_at"]
    search_fields = ["settlement__producer__username", "notes"]
    readonly_fields = ["id", "created_at"]
