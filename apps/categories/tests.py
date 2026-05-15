import pytest

from apps.categories.models import Category
from apps.products.models import Product

pytestmark = pytest.mark.django_db


def test_tc004_category_browsing_returns_only_available_products(producer_user):
    vegetables = Category.objects.create(name="Vegetables")
    dairy = Category.objects.create(name="Dairy Products")

    veg_products = [
        Product.objects.create(
            producer=producer_user,
            category=vegetables,
            name=f"Vegetable {i}",
            description="Available vegetable",
            price="2.00",
            unit="kg",
            stock_quantity=10,
            is_available=True,
        )
        for i in range(5)
    ]
    dairy_products = [
        Product.objects.create(
            producer=producer_user,
            category=dairy,
            name=f"Dairy {i}",
            description="Available dairy product",
            price="3.00",
            unit="litre",
            stock_quantity=8,
            is_available=True,
        )
        for i in range(3)
    ]
    hidden = Product.objects.create(
        producer=producer_user,
        category=vegetables,
        name="Unavailable Vegetable",
        description="No stock",
        price="1.00",
        stock_quantity=0,
        is_available=True,
    )

    vegetable_results = Product.objects.active().filter(category=vegetables)
    dairy_results = Product.objects.active().filter(category=dairy)

    assert set(veg_products).issubset(set(vegetable_results))
    assert hidden not in vegetable_results
    assert set(dairy_products) == set(dairy_results)
