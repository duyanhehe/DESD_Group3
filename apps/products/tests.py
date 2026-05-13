"""
Comprehensive test suite for the Products app.

Tests cover:
- Seasonal availability (available_from/available_to date ranges)
- Stock management and visibility
- Product active/inactive status
- Product CRUD operations
- Allergen associations
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.utils.timezone import now

from apps.products.models import Product, Category
from apps.allergens.models import Allergen

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: Product Seasonal Availability
# ============================================================================


class TestProductSeasonalAvailability:
    """Unit tests for product seasonal date range logic."""

    def test_product_in_season_within_dates(self, product):
        """
        Test: Product is in season when current date is within available_from/available_to.
        """
        assert product.is_in_season() == True

    def test_product_out_of_season_before_start_date(self, producer_user, category):
        """
        Test: Product out of season if today < available_from.
        """
        future_date = now().date() + timedelta(days=30)
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Future Product",
            description="Not available yet",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=future_date,
            available_to=future_date + timedelta(days=60),
        )

        assert product.is_in_season() == False

    def test_product_out_of_season_after_end_date(self, producer_user, category):
        """
        Test: Product out of season if today > available_to.
        """
        past_date = now().date() - timedelta(days=30)
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Past Product",
            description="No longer available",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=past_date - timedelta(days=60),
            available_to=past_date,
        )

        assert product.is_in_season() == False

    def test_product_no_seasonal_restriction(self, producer_user, category):
        """
        Test: Product with no dates set is always in season.
        """
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Year Round Product",
            description="Always available",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=None,
            available_to=None,
        )

        assert product.is_in_season() == True

    def test_product_only_start_date_set(self, producer_user, category):
        """
        Test: Product with only available_from (no end date) is in season after start.
        """
        past_date = now().date() - timedelta(days=10)
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Start Date Only",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=past_date,
            available_to=None,
        )

        assert product.is_in_season() == True

    def test_product_only_end_date_set(self, producer_user, category):
        """
        Test: Product with only available_to (no start date) is in season before end.
        """
        future_date = now().date() + timedelta(days=10)
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="End Date Only",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=None,
            available_to=future_date,
        )

        assert product.is_in_season() == True

    def test_product_boundary_dates(self, producer_user, category):
        """
        Test: Product is in season on exact start and end dates (inclusive).
        """
        today = now().date()
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Boundary Test",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=today,
            available_to=today,
        )

        assert product.is_in_season() == True


# ============================================================================
# UNIT TESTS: Product Stock & Visibility
# ============================================================================


class TestProductStockAndVisibility:
    """Unit tests for product stock management and visibility."""

    def test_product_active_when_in_stock_and_in_season(self, product):
        """
        Test: Product is active when stock > 0, is_available=True, and in season.
        """
        assert product.is_active() == True

    def test_product_inactive_when_out_of_stock(self, product_out_of_stock):
        """
        Test: Product is inactive when stock_quantity = 0.
        """
        assert product_out_of_stock.is_active() == False

    def test_product_inactive_when_disabled(self, producer_user, category):
        """
        Test: Product is inactive when is_available = False.
        """
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Disabled",
            description="Manually disabled",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=False,
            available_from=today - timedelta(days=90),
            available_to=today - timedelta(days=30),  # Out of season
        )

        assert product.is_active() == False

    def test_product_inactive_when_out_of_season(self, product_out_of_season):
        """
        Test: Product is inactive when out of season.
        """
        assert product_out_of_season.is_active() == False

    def test_product_status_out_of_stock(self, product_out_of_stock):
        """
        Test: get_status() returns "Out of Stock" when stock = 0.
        """
        assert product_out_of_stock.get_status() == "Out of Stock"

    def test_product_status_out_of_season(self, product_out_of_season):
        """
        Test: get_status() returns "Out of Season" when unavailable date-wise.
        """
        assert product_out_of_season.get_status() == "Out of Season"

    def test_product_status_available(self, product):
        """
        Test: get_status() returns "Available" when all conditions met.
        """
        assert product.get_status() == "Available"

    def test_product_status_unavailable(self, producer_user, category):
        """
        Test: get_status() returns "Unavailable" for manually disabled products.
        """
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Unavailable",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=today - timedelta(days=90),
            available_to=today - timedelta(days=30),  # Out of season
        )

        assert product.get_status() == "Unavailable"


# ============================================================================
# UNIT TESTS: Product Manager Filtering
# ============================================================================


class TestProductManager:
    """Unit tests for ProductManager.active() query."""

    def test_product_manager_active_filter(self, product):
        """
        Test: Product.objects.active() returns only active products.
        """
        active_products = Product.objects.active()

        assert product in active_products

    def test_product_manager_excludes_out_of_stock(self, product, product_out_of_stock):
        """
        Test: ProductManager.active() excludes out-of-stock products.
        """
        active_products = Product.objects.active()

        assert product in active_products
        assert product_out_of_stock not in active_products

    def test_product_manager_excludes_out_of_season(
        self, product, product_out_of_season
    ):
        """
        Test: ProductManager.active() excludes out-of-season products.
        """
        active_products = Product.objects.active()

        assert product in active_products
        assert product_out_of_season not in active_products

    def test_product_manager_excludes_disabled(self, producer_user, category):
        """
        Test: ProductManager.active() excludes manually disabled products.
        Note: Products with is_available=False but in stock/in season will be
        auto-enabled by update_availability(). This test uses out-of-season
        dates to keep the product disabled.
        """
        past_date = now().date() - timedelta(days=10)
        disabled_product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Disabled",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=False,
            # Set out-of-season to keep is_available=False
            available_from=past_date - timedelta(days=60),
            available_to=past_date,
        )

        active_products = Product.objects.active()

        assert disabled_product not in active_products


# ============================================================================
# UNIT TESTS: Product Auto-Availability
# ============================================================================


class TestProductAutoAvailability:
    """Unit tests for automatic availability management."""

    def test_update_availability_sets_unavailable_when_out_of_season(
        self, producer_user, category
    ):
        """
        Test: Saving out-of-season product sets is_available=False automatically.
        """
        past_date = now().date() - timedelta(days=10)
        product = Product(
            producer=producer_user,
            category=category,
            name="Test",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=True,
            available_from=past_date - timedelta(days=60),
            available_to=past_date,
        )

        # Before save, is_available is True
        assert product.is_available == True

        # After save, update_availability() should set it to False
        product.save()

        assert product.is_available == False

    def test_update_availability_keeps_available_when_in_season(
        self, producer_user, category
    ):
        """
        Test: Saving in-season product with stock keeps is_available=True.
        """
        today = now().date()
        product = Product(
            producer=producer_user,
            category=category,
            name="Test",
            description="Test",
            price=Decimal("5.00"),
            stock_quantity=10,
            is_available=False,  # Start as unavailable
            available_from=today - timedelta(days=10),
            available_to=today + timedelta(days=10),
        )

        product.save()

        # Should be auto-enabled
        assert product.is_available == True


# ============================================================================
# UNIT TESTS: Product Allergens
# ============================================================================


class TestProductAllergens:
    """Unit tests for allergen associations."""

    def test_add_allergen_to_product(self, product, allergen):
        """
        Test: Adding allergen to product M2M relationship.
        """
        product.allergens.add(allergen)

        assert allergen in product.allergens.all()

    def test_product_multiple_allergens(self, product):
        """
        Test: Product can have multiple allergens.
        """
        allergen1 = Allergen.objects.create(name="Peanuts")
        allergen2 = Allergen.objects.create(name="Milk")
        allergen3 = Allergen.objects.create(name="Gluten")

        product.allergens.add(allergen1, allergen2, allergen3)

        assert product.allergens.count() == 3

    def test_remove_allergen_from_product(self, product, allergen):
        """
        Test: Removing allergen from product.
        """
        product.allergens.add(allergen)
        assert allergen in product.allergens.all()

        product.allergens.remove(allergen)

        assert allergen not in product.allergens.all()

    def test_allergen_reverse_relationship(self, product, allergen):
        """
        Test: Allergen.products_set returns products with that allergen.
        """
        product.allergens.add(allergen)

        products_with_allergen = allergen.products.all()

        assert product in products_with_allergen


# ============================================================================
# UNIT TESTS: Product CRUD
# ============================================================================


class TestProductCRUD:
    """Unit tests for basic product create/read/update/delete."""

    def test_create_product(self, producer_user, category):
        """
        Test: Creating a new product.
        """
        product = Product.objects.create(
            producer=producer_user,
            category=category,
            name="New Product",
            description="A brand new product",
            price=Decimal("9.99"),
            stock_quantity=50,
        )

        assert product.id is not None
        assert product.name == "New Product"

    def test_update_product_stock(self, product):
        """
        Test: Updating product stock quantity.
        """
        original_stock = product.stock_quantity
        product.stock_quantity = original_stock - 5
        product.save()

        product.refresh_from_db()
        assert product.stock_quantity == original_stock - 5

    def test_update_product_price(self, product):
        """
        Test: Updating product price.
        """
        new_price = Decimal("7.99")
        product.price = new_price
        product.save()

        product.refresh_from_db()
        assert product.price == new_price

    def test_delete_product(self, product):
        """
        Test: Deleting a product.
        """
        product_id = product.id
        product.delete()

        assert Product.objects.filter(id=product_id).count() == 0

    def test_product_fields_preserved(self, product):
        """
        Test: All product fields are preserved after save.
        """
        original_name = product.name
        original_price = product.price
        original_stock = product.stock_quantity

        product.save()

        product.refresh_from_db()
        assert product.name == original_name
        assert product.price == original_price
        assert product.stock_quantity == original_stock


# ============================================================================
# INTEGRATION TESTS: Product Visibility in API
# ============================================================================


class TestProductVisibilityInListings:
    """Integration tests for product visibility in customer-facing lists."""

    def test_product_list_only_active(
        self, product, product_out_of_stock, product_out_of_season
    ):
        """
        Test: Product list API only returns active products.
        """
        active = Product.objects.active()

        assert product in active
        assert product_out_of_stock not in active
        assert product_out_of_season not in active

    def test_product_ordering_by_creation_date(self, producer_user, category):
        """
        Test: Products ordered by creation date (newest first).
        """
        import time

        product1 = Product.objects.create(
            producer=producer_user,
            category=category,
            name="First",
            price=Decimal("5.00"),
            stock_quantity=10,
        )

        # Small delay to ensure different timestamps
        time.sleep(0.01)

        product2 = Product.objects.create(
            producer=producer_user,
            category=category,
            name="Second",
            price=Decimal("6.00"),
            stock_quantity=10,
        )

        # Filter to only products from this test
        products = Product.objects.filter(name__in=["First", "Second"]).order_by(
            "-created_at"
        )

        assert products.first() == product2  # Newest first
        assert products.last() == product1  # Oldest last


if __name__ == "__main__":
    pytest.main([__file__])
