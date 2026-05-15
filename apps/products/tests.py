from decimal import Decimal

import pytest
from django.utils.timezone import now

from apps.allergens.models import Allergen
from apps.categories.models import Category
from apps.orders.models import Order, OrderItem
from apps.products.models import FarmStory, Product, Recipe, Review

pytestmark = pytest.mark.django_db


def test_tc003_producer_can_list_new_product_with_required_marketplace_details(
    producer_user,
):
    category = Category.objects.create(name="Dairy & Eggs")
    eggs = Allergen.objects.create(name="Eggs")

    product = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Organic Free Range Eggs",
        description="Fresh organic eggs from free-range hens, collected daily",
        price=Decimal("3.50"),
        unit="Dozen",
        stock_quantity=50,
        is_available=True,
        available_from=now().date(),
        is_organic=True,
    )
    product.allergens.add(eggs)

    assert product.producer == producer_user
    assert product in Product.objects.active()
    assert product.category.name == "Dairy & Eggs"
    assert product.unit == "Dozen"
    assert list(product.allergens.values_list("name", flat=True)) == ["Eggs"]


def test_tc005_customer_search_finds_products_by_name_description_and_producer(
    producer_user, category
):
    producer_user.producer_profile.business_name = "Organic Bristol Growers"
    producer_user.producer_profile.save()
    tomato = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Heritage Tomatoes",
        description="Sweet seasonal salad tomatoes",
        price=Decimal("4.20"),
        stock_quantity=20,
    )
    carrots = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Organic Carrots",
        description="Fresh roots",
        price=Decimal("2.30"),
        stock_quantity=30,
        is_organic=True,
    )

    tomato_results = Product.objects.active().filter(name__icontains="tomatoes")
    organic_results = (
        Product.objects.active().filter(description__icontains="organic")
        | Product.objects.active().filter(name__icontains="organic")
        | Product.objects.active().filter(
            producer__producer_profile__business_name__icontains="organic"
        )
    )
    missing_results = Product.objects.active().filter(name__icontains="dragonfruit")

    assert list(tomato_results) == [tomato]
    assert carrots in organic_results
    assert tomato in organic_results
    assert list(missing_results) == []


def test_tc011_producer_updates_inventory_so_unavailable_products_are_hidden(product):
    product.stock_quantity = 0
    product.save()

    assert product.get_status() == "Out of Stock"
    assert product not in Product.objects.active()

    product.stock_quantity = 25
    product.save()

    assert product.get_status() == "Available"
    assert product in Product.objects.active()


def test_tc014_customer_can_filter_certified_organic_products(producer_user, category):
    organic = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Certified Organic Kale",
        description="Certified organic",
        price=Decimal("2.50"),
        stock_quantity=12,
        is_organic=True,
    )
    conventional = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Conventional Kale",
        description="Local produce",
        price=Decimal("1.80"),
        stock_quantity=12,
        is_organic=False,
    )

    organic_results = Product.objects.active().filter(is_organic=True)

    assert organic in organic_results
    assert conventional not in organic_results


def test_tc016_producer_sets_seasonal_availability_for_products(
    producer_user, category
):
    current_month = now().date().month
    next_month = 1 if current_month == 12 else current_month + 1
    seasonal = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Seasonal Strawberries",
        description="In season now",
        price=Decimal("4.00"),
        stock_quantity=15,
        season_start_month=current_month,
        season_end_month=next_month,
    )
    out_of_season = Product.objects.create(
        producer=producer_user,
        category=category,
        name="Winter Squash",
        description="Not in season now",
        price=Decimal("3.00"),
        stock_quantity=15,
        season_start_month=next_month,
        season_end_month=next_month,
    )

    assert seasonal.is_in_season() is True
    assert seasonal in Product.objects.active()
    assert out_of_season.is_in_season() is False
    assert out_of_season not in Product.objects.active()


def test_tc019_producer_can_mark_surplus_produce_with_discount(product):
    product.is_surplus = True
    product.discount_price = Decimal("1.99")
    product.save()

    surplus_results = Product.objects.active().filter(is_surplus=True)

    assert product in surplus_results
    assert product.effective_price == Decimal("1.99")
    assert product.effective_price < product.price


def test_tc020_producer_can_share_recipes_and_farm_stories(producer_user, product):
    recipe = Recipe.objects.create(
        producer=producer_user,
        title="Apple Crumble",
        content="Use local apples for a seasonal dessert.",
    )
    story = FarmStory.objects.create(
        producer=producer_user,
        title="Harvest Week",
        content="A story from the farm.",
    )
    recipe.products.add(product)
    story.products.add(product)

    assert recipe in producer_user.recipes.all()
    assert story in producer_user.stories.all()
    assert product in recipe.products.all()
    assert product in story.products.all()


def test_tc023_low_stock_notification_data_is_available_to_producer(product):
    product.low_stock_threshold = 5
    product.stock_quantity = 4
    product.save()

    low_stock_alerts = [
        item
        for item in Product.objects.filter(producer=product.producer)
        if item.stock_quantity <= item.low_stock_threshold
    ]

    assert product in low_stock_alerts


def test_tc024_customer_can_rate_and_review_a_purchased_product(
    customer_user, producer_user, product
):
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.DELIVERED,
        total_price=Decimal("3.99"),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=1,
        unit_price=product.price,
    )

    review = Review.objects.create(
        product=product,
        customer=customer_user,
        rating=5,
        comment="Excellent local produce.",
    )

    assert review in product.reviews.all()
    assert product.reviews.first().rating == 5
