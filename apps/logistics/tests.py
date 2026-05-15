import pytest

from apps.logistics.utils import haversine_distance
from apps.orders.models import Cart, CartItem

pytestmark = pytest.mark.django_db


def test_tc013_customer_can_view_food_miles_for_cart_product(
    customer_user, product, monkeypatch
):
    def fake_distance(producer_postcode, customer_postcode):
        assert producer_postcode == product.producer.producer_profile.postcode
        assert customer_postcode == customer_user.customer_profile.postcode
        return 15.2

    monkeypatch.setattr(
        "apps.logistics.utils.calculate_distance_between_postcodes",
        fake_distance,
    )
    cart = Cart.objects.create(customer=customer_user)
    item = CartItem.objects.create(cart=cart, product=product, quantity=1)

    assert item.food_miles == 15.2
    assert cart.total_food_miles == 15.2


def test_tc013_food_miles_distance_calculation_uses_known_locations():
    bristol = (51.4545, -2.5879)
    yate = (51.5235, -2.3698)

    distance = haversine_distance(bristol[0], bristol[1], yate[0], yate[1])

    assert 9 < distance < 13
