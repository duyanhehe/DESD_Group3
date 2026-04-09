from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusLog


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "updated_at")
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


class StatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "timestamp")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_price", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline, StatusLogInline]


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ("order", "old_status", "new_status", "changed_by", "timestamp")
    list_filter = ("new_status",)
