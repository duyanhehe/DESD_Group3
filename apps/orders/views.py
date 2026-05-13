from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.timezone import now

from .models import Cart, CartItem, Order, OrderItem, OrderStatusLog
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderStatusLogSerializer,
    ProducerOrderSerializer,
)
from apps.products.models import Product
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import RefundRequest
from .serializers import RefundRequestSerializer
from .services import RefundService, RefundServiceError


@login_required
def cart_page(request):
    return render(request, "orders/cart.html")


@login_required
def order_success_page(request):
    return render(request, "orders/success.html")


@login_required
def producer_orders_page(request):
    if not request.user.is_producer:
        return redirect("/")
    return render(request, "orders/producer_order_list.html")


@login_required
def order_history_page(request):
    return render(request, "orders/order_history.html")


# ─── Cart Views (DESD-55, 56, 57, 58) ──────────────────────


class CartDetailView(APIView):
    """GET — return the current user's cart with items, totals,
    and producer grouping. Cart is created on first access."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class AddToCartView(APIView):
    """POST — add a product to cart. If already in cart, bump the quantity."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only customers can add to cart
        if not request.user.is_customer:
            return Response(
                {"error": "Only customers can add items to cart."},
                status=status.HTTP_403_FORBIDDEN,
            )

        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if quantity < 1:
            return Response(
                {"error": "Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = get_object_or_404(Product, id=product_id)

        # don't allow adding inactive / out-of-season products
        if not product.is_active():
            return Response(
                {"error": "This product is currently unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > product.stock_quantity:
            return Response(
                {"error": f"Only {product.stock_quantity} available in stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, _ = Cart.objects.get_or_create(customer=request.user)

        # if product already in cart, add to existing quantity
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            new_qty = cart_item.quantity + quantity
            if new_qty > product.stock_quantity:
                return Response(
                    {
                        "error": f"Can't add more. Only {product.stock_quantity} in stock."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart_item.quantity = new_qty
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    """PUT — update quantity of a cart item. Send quantity=0 to remove."""

    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)
        quantity = int(request.data.get("quantity", 0))

        if quantity < 0:
            return Response(
                {"error": "Quantity can't be negative."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # quantity 0 = remove
        if quantity == 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product.stock_quantity:
                return Response(
                    {"error": f"Only {cart_item.product.stock_quantity} available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart_item.quantity = quantity
            cart_item.save()

        cart = Cart.objects.get(customer=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class RemoveCartItemView(APIView):
    """DELETE — remove an item from the cart."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)
        cart_item.delete()

        cart = Cart.objects.get(customer=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class ClearCartView(APIView):
    """DELETE — empty the entire cart."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_object_or_404(Cart, customer=request.user)
        cart.items.all().delete()
        serializer = CartSerializer(cart)
        return Response(serializer.data)


# ─── Order Views (DESD-71, 72, 73) ─────────────────────────


class CreateOrderView(APIView):
    """POST — create an order from the current cart contents.
    Clears the cart after order is placed."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, customer=request.user)
        cart_items = cart.items.select_related("product").all()

        if not cart_items.exists():
            return Response(
                {"error": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # double-check everything is still in stock
        for item in cart_items:
            if not item.product.is_active():
                return Response(
                    {"error": f"'{item.product.name}' is no longer available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if item.quantity > item.product.stock_quantity:
                return Response(
                    {"error": f"Not enough stock for '{item.product.name}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            # calculate total
            total = sum(item.product.price * item.quantity for item in cart_items)

            # 1. Create Master Order
            master_order = Order.objects.create(
                customer=request.user,
                status=Order.PENDING,
                total_price=total,
            )

            OrderStatusLog.objects.create(
                order=master_order,
                old_status="",
                new_status=Order.PENDING,
                changed_by=request.user,
                note="Master Order placed",
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
                    customer=request.user,
                    parent_order=master_order,
                    producer=producer,
                    status=Order.PENDING,
                    total_price=sub_total,
                )

                OrderStatusLog.objects.create(
                    order=sub_order,
                    old_status="",
                    new_status=Order.PENDING,
                    changed_by=request.user,
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

            # clear the cart
            cart.items.all().delete()

        serializer = OrderSerializer(master_order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CustomerOrderListView(APIView):
    """GET — list all orders for the logged-in customer."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only list Master Orders for the customer
        orders = Order.objects.filter(customer=request.user, parent_order__isnull=True)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class CustomerOrderDetailView(APIView):
    """GET — single order detail for the customer."""

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # A customer can view their Master Order or Sub-Orders
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class ReorderView(APIView):
    """POST — Reorder items from a past order.
    Checks availability and adds items to the current cart.
    Handles Master Orders (fetches items from sub-orders) or Sub-Orders directly."""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        cart, _ = Cart.objects.get_or_create(customer=request.user)

        # Get all items (from sub-orders if master, or directly if sub-order)
        if order.parent_order is None and order.sub_orders.exists():
            items = OrderItem.objects.filter(order__parent_order=order)
        else:
            items = order.items.all()

        added_items = []
        unavailable_items = []
        partial_items = []

        for item in items:
            product = item.product

            if not product.is_active() or product.stock_quantity == 0:
                unavailable_items.append(
                    {"name": product.name, "reason": "Out of stock or off-season"}
                )
                continue

            qty_to_add = item.quantity
            if qty_to_add > product.stock_quantity:
                qty_to_add = product.stock_quantity
                partial_items.append(
                    {
                        "name": product.name,
                        "requested": item.quantity,
                        "added": qty_to_add,
                        "reason": f"Only {qty_to_add} left in stock",
                    }
                )
            else:
                added_items.append({"name": product.name, "added": qty_to_add})

            # Add to cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={"quantity": qty_to_add},
            )
            if not created:
                new_qty = cart_item.quantity + qty_to_add
                # Ensure we don't exceed stock when combining with existing cart
                if new_qty > product.stock_quantity:
                    new_qty = product.stock_quantity
                cart_item.quantity = new_qty
                cart_item.save()

        # Generate summary message
        msg_parts = []
        if added_items or partial_items:
            msg_parts.append(
                f"Successfully added {len(added_items) + len(partial_items)} items to your cart."
            )
        if unavailable_items:
            msg_parts.append(
                f"{len(unavailable_items)} items were unavailable and skipped."
            )

        summary = (
            " ".join(msg_parts) if msg_parts else "No items were available to reorder."
        )

        return Response(
            {
                "message": summary,
                "details": {
                    "added": added_items,
                    "partial": partial_items,
                    "unavailable": unavailable_items,
                },
            },
            status=status.HTTP_200_OK,
        )


class UpdateOrderStatusView(APIView):
    """PUT — producer updates order status.
    Enforces: PENDING → CONFIRMED → READY → DELIVERED.
    Auto-logs every change to OrderStatusLog (audit trail)."""

    permission_classes = [IsAuthenticated]

    def put(self, request, order_id):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can update order status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(Order, id=order_id)

        # make sure this producer actually has items in the order
        has_items = order.items.filter(producer=request.user).exists()
        if not has_items:
            return Response(
                {"error": "You don't have any items in this order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Missing 'status' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # check if the transition is valid
        if not order.can_transition_to(new_status):
            allowed = Order.VALID_TRANSITIONS.get(order.status, [])
            return Response(
                {
                    "error": f"Can't go from '{order.status}' to '{new_status}'.",
                    "allowed_transitions": allowed,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = order.status
        note = request.data.get("note", "")

        order.status = new_status

        # Set delivered_at timestamp when order is marked as delivered
        if new_status == Order.DELIVERED and not order.delivered_at:
            order.delivered_at = now()

        order.save()

        # audit trail
        OrderStatusLog.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            note=note,
        )

        # Sync UP to Master Order
        if order.parent_order:
            parent = order.parent_order
            sub_statuses = [so.status for so in parent.sub_orders.all()]

            # Only update master when ALL sub-orders reach the same status
            if all(s == new_status for s in sub_statuses):
                new_parent_status = new_status
            else:
                new_parent_status = parent.status  # don't change yet

            if parent.status != new_parent_status:
                old_p_status = parent.status
                parent.status = new_parent_status
                if new_parent_status == Order.DELIVERED and not parent.delivered_at:
                    parent.delivered_at = now()
                parent.save()

                OrderStatusLog.objects.create(
                    order=parent,
                    old_status=old_p_status,
                    new_status=new_parent_status,
                    changed_by=request.user,
                    note=f"Auto-synced from sub-order",
                )

        serializer = OrderSerializer(order)
        return Response(serializer.data)


class OrderStatusHistoryView(APIView):
    """GET — full audit trail of status changes for an order."""

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        # customers can see their own, producers can see orders they're in
        is_customer = order.customer == request.user
        is_producer = order.items.filter(producer=request.user).exists()
        if not (is_customer or is_producer):
            return Response(
                {"error": "You don't have access to this order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        logs = order.status_logs.all()
        serializer = OrderStatusLogSerializer(logs, many=True)
        return Response(serializer.data)


# ─── Producer Order Views (DESD-66, 67, 68) ────────────────


class ProducerOrderListView(APIView):
    """GET — list orders that contain this producer's products.
    Only shows items belonging to this producer (not other vendors)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access this."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # find all orders that have at least one item from this producer
        order_ids = (
            OrderItem.objects.filter(producer=request.user)
            .values_list("order_id", flat=True)
            .distinct()
        )
        orders = Order.objects.filter(id__in=order_ids)
        serializer = ProducerOrderSerializer(
            orders, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ProducerOrderDetailView(APIView):
    """GET — single order detail from the producer's perspective.
    Includes customer contact info for delivery coordination."""

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        if not request.user.is_producer:
            return Response(
                {"error": "Only producers can access this."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(Order, id=order_id)

        # verify this producer has items in the order
        has_items = order.items.filter(producer=request.user).exists()
        if not has_items:
            return Response(
                {"error": "You don't have any items in this order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProducerOrderSerializer(order, context={"request": request})
        return Response(serializer.data)


# ─── Refund Views ──────────────────────────────────────────


class CustomerRefundRequestView(APIView):
    """POST — Customer requests a refund."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order_item_id = request.data.get("order_item_id")
        reason_category = request.data.get("reason_category")
        reason_text = request.data.get("reason_text", "")
        evidence_image = request.FILES.get("evidence_image")

        if not order_id or not reason_category:
            return Response(
                {"error": "Missing order_id or reason_category"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = get_object_or_404(Order, id=order_id, customer=request.user)

        if not order.can_transition_to(Order.REFUND_REQUESTED):
            return Response(
                {"error": f"Cannot request refund for order in status {order.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate pending refund requests for the same order
        if RefundRequest.objects.filter(
            order=order, status=RefundRequest.STATUS_PENDING
        ).exists():
            return Response(
                {"error": "A refund request is already pending for this order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_item = None
        if order_item_id:
            # OrderItem belongs to a sub-order, so we filter by order__parent_order=order
            order_item = get_object_or_404(
                OrderItem, id=order_item_id, order__parent_order=order
            )

        # Validate delivery rules
        if reason_category in [
            RefundRequest.REASON_SPOILED,
            RefundRequest.REASON_FRESH_RETURN,
        ]:
            if order.status != Order.DELIVERED:
                return Response(
                    {"error": "Order must be delivered to return items."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if order.delivered_at:
                delta = now() - order.delivered_at
                if delta.days > 2:
                    return Response(
                        {"error": "Return window (2 days) has expired."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if reason_category == RefundRequest.REASON_SPOILED and not evidence_image:
                return Response(
                    {"error": "Evidence image is required for spoiled items."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if (
            reason_category == RefundRequest.REASON_NOT_DELIVERED
            and order.status == Order.DELIVERED
        ):
            return Response(
                {"error": "Order is already delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_amount = RefundService.calculate_refund_amount(
                order, order_item, reason_category
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            refund_req = RefundRequest.objects.create(
                order=order,
                order_item=order_item,
                customer=request.user,
                reason_category=reason_category,
                reason_text=reason_text,
                evidence_image=evidence_image,
                requested_amount=requested_amount,
            )

            old_status = order.status
            order.status = Order.REFUND_REQUESTED
            order.save()

            OrderStatusLog.objects.create(
                order=order,
                old_status=old_status,
                new_status=Order.REFUND_REQUESTED,
                changed_by=request.user,
                note="Customer requested a refund",
            )

            # Sync sub-orders
            for sub_order in order.sub_orders.all():
                if sub_order.can_transition_to(Order.REFUND_REQUESTED):
                    sub_order.status = Order.REFUND_REQUESTED
                    sub_order.save()
                    OrderStatusLog.objects.create(
                        order=sub_order,
                        old_status=old_status,
                        new_status=Order.REFUND_REQUESTED,
                        changed_by=request.user,
                        note="Customer requested a refund for Master Order",
                    )

        serializer = RefundRequestSerializer(refund_req)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminRefundReviewView(APIView):
    """POST — Admin approves or rejects a refund request."""

    permission_classes = [IsAuthenticated]

    def post(self, request, refund_id):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN
            )

        refund_req = get_object_or_404(RefundRequest, id=refund_id)
        action = request.data.get("action")  # 'approve' or 'reject'
        admin_note = request.data.get("admin_note", "")

        if action not in ["approve", "reject"]:
            return Response(
                {"error": "Action must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if action == "approve":
                refund_req = RefundService.process_refund_approval(
                    refund_req, request.user, admin_note
                )
            else:
                refund_req = RefundService.reject_refund(
                    refund_req, request.user, admin_note
                )

            serializer = RefundRequestSerializer(refund_req)
            return Response(
                {"message": f"Refund {action}d successfully", "data": serializer.data}
            )

        except RefundServiceError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminRefundListView(APIView):
    """GET — List all refund requests with status filtering."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN
            )

        refunds = RefundRequest.objects.all().order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            refunds = refunds.filter(status=status_filter.lower())

        serializer = RefundRequestSerializer(refunds, many=True)
        return Response(serializer.data)


class AdminRefundReviewPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """TemplateView for the admin refund review dashboard. Staff-only access."""

    template_name = "orders/admin_refunds.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Refund Review Dashboard"
        return context
