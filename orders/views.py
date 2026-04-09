from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Cart, CartItem, Order, OrderItem, OrderStatusLog
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderStatusLogSerializer,
    ProducerOrderSerializer,
)
from products.models import Product
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def cart_page(request):
    return render(request, "orders/cart.html")


@login_required
def producer_orders_page(request):
    if not request.user.is_producer:
        return redirect("/")
    return render(request, "orders/producer_order_list.html")


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
            cart=cart, product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            new_qty = cart_item.quantity + quantity
            if new_qty > product.stock_quantity:
                return Response(
                    {"error": f"Can't add more. Only {product.stock_quantity} in stock."},
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
        cart_item = get_object_or_404(
            CartItem, id=item_id, cart__customer=request.user
        )
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
        cart_item = get_object_or_404(
            CartItem, id=item_id, cart__customer=request.user
        )
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

            order = Order.objects.create(
                customer=request.user,
                status=Order.PENDING,
                total_price=total,
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    producer=item.product.producer,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                )
                # deduct stock
                item.product.stock_quantity -= item.quantity
                item.product.save()

            # log the initial status
            OrderStatusLog.objects.create(
                order=order,
                old_status="",
                new_status=Order.PENDING,
                changed_by=request.user,
                note="Order placed",
            )

            # clear the cart
            cart.items.all().delete()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CustomerOrderListView(APIView):
    """GET — list all orders for the logged-in customer."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(customer=request.user)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class CustomerOrderDetailView(APIView):
    """GET — single order detail for the customer."""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


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
        order.save()

        # audit trail
        OrderStatusLog.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            note=note,
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
            OrderItem.objects
            .filter(producer=request.user)
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

        serializer = ProducerOrderSerializer(
            order, context={"request": request}
        )
        return Response(serializer.data)
