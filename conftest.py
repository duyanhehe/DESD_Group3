"""
Pytest configuration and shared fixtures for the DESD Food Network testing suite.
Provides:
- Django test database setup
- User factories and fixtures
- Mock external APIs (Stripe, Nominatim)
- Common test utilities
"""

import os
import django
from decimal import Decimal
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils.timezone import now, make_aware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.accounts.models import CustomerProfile, ProducerProfile
from apps.products.models import Product, Category
from apps.allergens.models import Allergen
from apps.orders.models import Cart, CartItem, Order, OrderItem, RefundRequest
from apps.payments.models import (
    ProducerWeeklySettlement,
    SettlementOrderItem,
    SettlementAuditLog,
    PaymentTransaction,
)

User = get_user_model()

# ============================================================================
# PYTEST CONFIGURATION & MARKERS
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "stripe: mark test as requiring Stripe")


# ============================================================================
# SESSION-SCOPED FIXTURES (once per test session)
# ============================================================================


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Configure Django test database and clear it between tests."""
    with django_db_blocker.unblock():
        pass


# ============================================================================
# FUNCTION-SCOPED FIXTURES (reset for each test)
# ============================================================================


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """Django REST Framework test client."""
    from rest_framework.test import APIClient

    return APIClient()


# ============================================================================
# USER & PROFILE FIXTURES
# ============================================================================


@pytest.fixture
def customer_user(db):
    """Create a test customer user."""
    user, _ = User.objects.get_or_create(
        username="testcustomer",
        defaults={
            "email": "customer@test.com",
            "password": "testpass123",
            "is_customer": True,
            "is_producer": False,
        },
    )
    # Update password if user already exists (get_or_create won't hash it)
    if user.password == "testpass123":
        user.set_password("testpass123")
        user.save()

    CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            "delivery_address": "123 Main Street",
            "postcode": "BS1 5AH",  # Bristol city centre
        },
    )
    return user


@pytest.fixture
def producer_user(db):
    """Create a test producer user."""
    user, _ = User.objects.get_or_create(
        username="testproducer",
        defaults={
            "email": "producer@test.com",
            "password": "testpass123",
            "is_customer": False,
            "is_producer": True,
        },
    )
    # Update password if user already exists
    if user.password == "testpass123":
        user.set_password("testpass123")
        user.save()

    ProducerProfile.objects.get_or_create(
        user=user,
        defaults={
            "business_name": "Test Farm Ltd",
            "business_address": "Farm Lane, Yate",
            "tax_id": "12345678",
            "farm_origin": "Yate, South Glos",
            "postcode": "BS37 7ER",  # Yate, South Glos
        },
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    user, _ = User.objects.get_or_create(
        username="testadmin",
        defaults={
            "email": "admin@test.com",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    # Set password if needed
    if user.password == "testpass123" or not user.password:
        user.set_password("testpass123")
        user.save()
    return user


@pytest.fixture
def multiple_customers(db):
    """Create multiple test customers."""
    customers = []
    for i in range(3):
        user = User.objects.create_user(
            username=f"customer{i}",
            email=f"customer{i}@test.com",
            password="testpass123",
            is_customer=True,
        )
        CustomerProfile.objects.create(
            user=user,
            postcode=f"BS{i} 1AA",
            delivery_address=f"{i} Test Road",
        )
        customers.append(user)
    return customers


@pytest.fixture
def multiple_producers(db):
    """Create multiple test producers."""
    producers = []
    for i in range(3):
        user = User.objects.create_user(
            username=f"producer{i}",
            email=f"producer{i}@test.com",
            password="testpass123",
            is_producer=True,
        )
        ProducerProfile.objects.create(
            user=user,
            business_name=f"Farm {i}",
            business_address=f"{i} Farm Road",
            postcode=f"BS{i} 7ER",
        )
        producers.append(user)
    return producers


# ============================================================================
# PRODUCT & CATEGORY FIXTURES
# ============================================================================


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(name="Vegetables", slug="vegetables")


@pytest.fixture
def allergen(db):
    """Create a test allergen with a unique name per test."""
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    allergen_name = f"Peanuts_{unique_suffix}"
    allergen = Allergen.objects.create(
        name=allergen_name, slug=allergen_name.lower().replace("_", "-")
    )
    return allergen


@pytest.fixture
def product(db, producer_user, category, allergen):
    """Create a test product (in season, in stock)."""
    today = now().date()
    product = Product.objects.create(
        producer=producer_user,
        name="Test Apples",
        category=category,
        description="Fresh organic apples",
        price=Decimal("3.99"),
        unit="kg",
        stock_quantity=100,
        is_available=True,
        available_from=today - timedelta(days=30),
        available_to=today + timedelta(days=30),
    )
    product.allergens.add(allergen)
    return product


@pytest.fixture
def product_out_of_season(db, producer_user, category):
    """Create a test product that is out of season."""
    today = now().date()
    return Product.objects.create(
        producer=producer_user,
        name="Out of Season Item",
        category=category,
        description="Out of season",
        price=Decimal("2.99"),
        stock_quantity=50,
        is_available=True,
        available_from=today - timedelta(days=90),
        available_to=today - timedelta(days=30),
    )


@pytest.fixture
def product_out_of_stock(db, producer_user, category):
    """Create a test product that is out of stock."""
    return Product.objects.create(
        producer=producer_user,
        name="Out of Stock Item",
        category=category,
        description="No stock",
        price=Decimal("5.99"),
        stock_quantity=0,
        is_available=True,
    )


@pytest.fixture
def products(db, producer_user, category):
    """Create multiple test products."""
    products = []
    for i in range(5):
        p = Product.objects.create(
            producer=producer_user,
            name=f"Product {i}",
            category=category,
            description=f"Test product {i}",
            price=Decimal(str(2.00 + i)),
            stock_quantity=50 + i * 10,
            is_available=True,
        )
        products.append(p)
    return products


# ============================================================================
# CART & ORDER FIXTURES
# ============================================================================


@pytest.fixture
def cart(db, customer_user):
    """Create a test cart."""
    return Cart.objects.create(customer=customer_user)


@pytest.fixture
def cart_with_items(db, cart, product):
    """Create a cart with items."""
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    return cart


@pytest.fixture
def order(db, customer_user, producer_user, product):
    """Create a test order (pending status)."""
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.PENDING,
        total_price=Decimal("50.00"),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=2,
        unit_price=product.price,
    )
    return order


@pytest.fixture
def delivered_order(db, customer_user, producer_user, product):
    """Create a delivered order (for settlement calculations)."""
    order = Order.objects.create(
        customer=customer_user,
        producer=producer_user,
        status=Order.DELIVERED,
        total_price=Decimal("50.00"),
        delivered_at=now(),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        producer=producer_user,
        quantity=2,
        unit_price=product.price,
    )
    return order


@pytest.fixture
def refund_request(db, order):
    """Create a refund request."""
    return RefundRequest.objects.create(
        order=order,
        customer=order.customer,
        status=RefundRequest.STATUS_PENDING,
        requested_amount=Decimal("25.00"),
        reason_category=RefundRequest.REASON_NOT_DELIVERED,
    )


# ============================================================================
# PAYMENT & SETTLEMENT FIXTURES
# ============================================================================


@pytest.fixture
def settlement(db, producer_user):
    """Create a test settlement."""
    today = now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    return ProducerWeeklySettlement.objects.create(
        producer=producer_user,
        week_start=week_start,
        week_end=week_end,
        total_sales=Decimal("100.00"),
        commission_rate=Decimal("0.05"),
        status=ProducerWeeklySettlement.STATUS_CALCULATED,
    )


@pytest.fixture
def payment_transaction(db, order, producer_user):
    """Create a payment transaction."""
    return PaymentTransaction.objects.create(
        order=order,
        stripe_payment_intent_id="pi_test123",
        total_amount=order.total_price,
        network_commission=order.total_price * Decimal("0.05"),
        producer_payout=order.total_price * Decimal("0.95"),
        status=PaymentTransaction.STATUS_SUCCEEDED,
    )


@pytest.fixture
def settlement_audit_log(db, settlement, admin_user):
    """Create a settlement audit log."""
    return SettlementAuditLog.objects.create(
        settlement=settlement,
        action="CREATED",
        performed_by=admin_user,
    )


# ============================================================================
# MOCK EXTERNAL SERVICES
# ============================================================================


@pytest.fixture
def mock_stripe():
    """Mock Stripe API client."""
    with patch("stripe.Refund.create") as mock_refund:
        mock_refund.return_value = Mock(id="re_test123", status="succeeded")
        yield mock_refund


@pytest.fixture
def mock_nominatim():
    """Mock Nominatim geocoding API."""
    import responses

    with responses.RequestsMock() as rsps:
        # Mock Bristol city centre postcode
        rsps.add(
            responses.GET,
            "https://nominatim.openstreetmap.org/search",
            json=[{"lat": "51.4545", "lon": "-2.5879"}],
            status=200,
            match=[responses.matchers.query_param_matcher({"q": "BS1 5AH"})],
        )
        # Mock Yate postcode
        rsps.add(
            responses.GET,
            "https://nominatim.openstreetmap.org/search",
            json=[{"lat": "51.5235", "lon": "-2.3698"}],
            status=200,
            match=[responses.matchers.query_param_matcher({"q": "BS37 7ER"})],
        )
        yield rsps


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture
def reset_cache(db):
    """Clear Django cache before and after test."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def freeze_time():
    """Fixture to freeze time for testing (if needed)."""
    # Can be expanded with freezegun if needed
    return now()
