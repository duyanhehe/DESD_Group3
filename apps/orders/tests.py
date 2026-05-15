from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from apps.accounts.models import CustomerProfile
from apps.orders.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatusLog,
    RecurringOrder,
    RecurringOrderItem,
)
from apps.products.models import Product

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_tc006_customer_adds_updates_and_removes_cart_items(
    customer_user, product, product_out_of_stock
):
    cart = Cart.objects.create(customer=customer_user)
    carrots = CartItem.objects.create(cart=cart, product=product, quantity=2)
    milk = CartItem.objects.create(cart=cart, product=product_out_of_stock, quantity=3)

    assert cart.items.count() == 2
    assert carrots.subtotal == product.effective_price * 2
    assert milk.subtotal == product_out_of_stock.effective_price * 3

    carrots.quantity = 3
    carrots.save()
    carrots.refresh_from_db()

    assert carrots.subtotal == product.effective_price * 3

    milk.delete()
    assert list(cart.items.values_list("product_id", flat=True)) == [product.id]


def test_tc007_customer_places_single_producer_order_with_48_hour_delivery(
    customer_user, producer_user, product
):
    delivery_date = now().date() + timedelta(days=2)
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.PENDING,
        delivery_date=delivery_date,
        total_price=Decimal("7.98"),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=2,
        unit_price=product.price,
    )

    assert order.status == Order.PENDING
    assert order.delivery_date >= now().date() + timedelta(days=2)
    assert order.items.count() == 1
    assert order.items.first().producer == producer_user


def test_tc008_customer_places_multi_vendor_order_with_linked_sub_orders(
    customer_user, producer_user, multiple_producers, category, product
):
    other_producer = multiple_producers[0]
    other_product = Product.objects.create(
        producer=other_producer,
        category=category,
        name="Fresh Milk",
        description="Local dairy",
        price=Decimal("2.00"),
        stock_quantity=20,
    )
    parent = Order.objects.create(
        customer=customer_user,
        status=Order.PENDING,
        total_price=Decimal("11.98"),
    )

    for producer, item_product, amount in [
        (producer_user, product, Decimal("7.98")),
        (other_producer, other_product, Decimal("4.00")),
    ]:
        sub_order = Order.objects.create(
            customer=customer_user,
            producer=producer,
            parent_order=parent,
            status=Order.PENDING,
            total_price=amount,
        )
        OrderItem.objects.create(
            order=sub_order,
            product=item_product,
            producer=producer,
            quantity=2,
            unit_price=item_product.price,
        )

    assert parent.sub_orders.count() == 2
    assert set(parent.sub_orders.values_list("producer_id", flat=True)) == {
        producer_user.id,
        other_producer.id,
    }
    assert all(order.items.count() == 1 for order in parent.sub_orders.all())


def test_tc009_producer_views_only_their_incoming_orders(
    customer_user, producer_user, multiple_producers, product, category
):
    other_producer = multiple_producers[0]
    other_product = Product.objects.create(
        producer=other_producer,
        category=category,
        name="Other Farm Product",
        description="Different producer",
        price=Decimal("2.50"),
        stock_quantity=10,
    )
    own_order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.PENDING,
        delivery_date=now().date() + timedelta(days=3),
        total_price=Decimal("3.99"),
    )
    other_order = Order.objects.create(
        customer=customer_user,
        producer=other_producer,
        status=Order.PENDING,
        delivery_date=now().date() + timedelta(days=4),
        total_price=Decimal("2.50"),
    )
    OrderItem.objects.create(
        order=own_order,
        product=product,
        producer=producer_user,
        quantity=1,
        unit_price=product.price,
    )
    OrderItem.objects.create(
        order=other_order,
        product=other_product,
        producer=other_producer,
        quantity=1,
        unit_price=other_product.price,
    )

    incoming = Order.objects.filter(producer=producer_user).order_by("delivery_date")

    assert list(incoming) == [own_order]
    assert other_order not in incoming
    assert incoming.first().items.first().product == product


def test_tc010_producer_updates_order_status_and_history_is_logged(
    order, producer_user
):
    old_status = order.status
    assert order.can_transition_to(Order.CONFIRMED)

    order.status = Order.CONFIRMED
    order.save()
    OrderStatusLog.objects.create(
        order=order,
        old_status=old_status,
        new_status=Order.CONFIRMED,
        changed_by=producer_user,
        note="Products will be prepared by delivery date",
    )

    assert order.can_transition_to(Order.READY)
    assert order.status_logs.count() == 1
    assert order.status_logs.first().new_status == Order.CONFIRMED


def test_tc017_community_group_bulk_order_gets_bulk_and_group_discount(
    producer_user, product
):
    group = User.objects.create_user(
        username="community.group@example.com",
        email="community.group@example.com",
        password="SecurePass123!",
        is_customer=True,
        is_community_group=True,
    )
    CustomerProfile.objects.create(
        user=group,
        delivery_address="Community Hall, Bristol",
        postcode="BS1 5JG",
    )
    cart = Cart.objects.create(customer=group)
    item = CartItem.objects.create(cart=cart, product=product, quantity=8)

    expected = product.effective_price * Decimal("0.75") * 8
    assert item.subtotal == expected


def test_tc018_restaurant_can_establish_regular_weekly_order(customer_user, product):
    recurring_order = RecurringOrder.objects.create(
        customer=customer_user,
        frequency_days=7,
        next_delivery_date=now().date() + timedelta(days=7),
    )
    item = RecurringOrderItem.objects.create(
        recurring_order=recurring_order,
        product=product,
        quantity=10,
    )

    assert recurring_order.is_active is True
    assert recurring_order.frequency_days == 7
    assert item in recurring_order.items.all()


def test_tc021_customer_can_view_order_history_for_reordering(
    customer_user, producer_user, product
):
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.DELIVERED,
        total_price=Decimal("7.98"),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=2,
        unit_price=product.price,
    )

    history = Order.objects.filter(customer=customer_user).prefetch_related("items")

    assert order in history
    assert history.first().items.first().product == product
