"""
Test suite for the Accounts app.

Tests cover:
- User creation (customer vs producer)
- Profile creation
- User authentication
- Role-based access
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import CustomerProfile, ProducerProfile

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================================================
# UNIT TESTS: User Creation
# ============================================================================


class TestUserCreation:
    """Unit tests for user creation and roles."""

    def test_create_customer_user(self):
        """
        Test: Creating a customer user.
        """
        user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="testpass123",
            is_customer=True,
            is_producer=False,
        )

        assert user.username == "john"
        assert user.is_customer == True
        assert user.is_producer == False

    def test_create_producer_user(self):
        """
        Test: Creating a producer user.
        """
        user = User.objects.create_user(
            username="farm",
            email="farm@example.com",
            password="testpass123",
            is_customer=False,
            is_producer=True,
        )

        assert user.username == "farm"
        assert user.is_customer == False
        assert user.is_producer == True

    def test_create_customer_and_producer_user(self):
        """
        Test: User can be both customer and producer.
        """
        user = User.objects.create_user(
            username="both",
            email="both@example.com",
            password="testpass123",
            is_customer=True,
            is_producer=True,
        )

        assert user.is_customer == True
        assert user.is_producer == True

    def test_user_defaults_to_customer(self):
        """
        Test: New user defaults to is_customer=True, is_producer=False.
        """
        user = User.objects.create_user(
            username="default",
            email="default@example.com",
            password="testpass123",
        )

        assert user.is_customer == True
        assert user.is_producer == False

    def test_create_superuser(self):
        """
        Test: Creating a superuser/admin.
        """
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )

        assert user.is_staff == True
        assert user.is_superuser == True


# ============================================================================
# UNIT TESTS: Customer Profile
# ============================================================================


class TestCustomerProfile:
    """Unit tests for customer profile creation and management."""

    def test_create_customer_profile(self, customer_user):
        """
        Test: Customer profile is created with address and postcode.
        """
        profile = customer_user.customer_profile

        assert profile.user == customer_user
        assert profile.postcode == "BS1 5AH"
        assert profile.delivery_address is not None

    def test_update_customer_postcode(self, customer_user):
        """
        Test: Updating customer postcode.
        """
        profile = customer_user.customer_profile
        new_postcode = "EC1A 1AA"

        profile.postcode = new_postcode
        profile.save()

        customer_user.refresh_from_db()
        assert customer_user.customer_profile.postcode == new_postcode

    def test_customer_profile_optional_fields(self):
        """
        Test: Delivery address can be blank/null.
        """
        user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="pass123",
        )

        profile = CustomerProfile.objects.create(user=user, postcode="BS1 5AH")

        assert profile.delivery_address is None
        assert profile.postcode == "BS1 5AH"


# ============================================================================
# UNIT TESTS: Producer Profile
# ============================================================================


class TestProducerProfile:
    """Unit tests for producer profile creation and management."""

    def test_create_producer_profile(self, producer_user):
        """
        Test: Producer profile contains business info.
        """
        profile = producer_user.producer_profile

        assert profile.user == producer_user
        assert profile.business_name == "Test Farm Ltd"
        assert profile.postcode == "BS37 7ER"

    def test_producer_profile_tax_id(self, producer_user):
        """
        Test: Producer can have tax ID for financial tracking.
        """
        profile = producer_user.producer_profile
        assert profile.tax_id == "12345678"

    def test_producer_profile_farm_origin(self, producer_user):
        """
        Test: Producer can specify farm origin/location.
        """
        profile = producer_user.producer_profile
        assert profile.farm_origin == "Yate, South Glos"

    def test_update_producer_business_name(self, producer_user):
        """
        Test: Updating business name.
        """
        profile = producer_user.producer_profile
        new_name = "Green Valley Organic Farm"

        profile.business_name = new_name
        profile.save()

        producer_user.refresh_from_db()
        assert producer_user.producer_profile.business_name == new_name


# ============================================================================
# UNIT TESTS: Phone Numbers
# ============================================================================


class TestPhoneNumbers:
    """Unit tests for phone number field."""

    def test_user_with_phone_number(self):
        """
        Test: User can have phone number.
        """
        user = User.objects.create_user(
            username="phone_user",
            email="phone@example.com",
            password="pass123",
            phone_number="+44 117 1234567",
        )

        assert user.phone_number == "+44 117 1234567"

    def test_phone_number_optional(self):
        """
        Test: Phone number is optional.
        """
        user = User.objects.create_user(
            username="no_phone",
            email="nophone@example.com",
            password="pass123",
        )

        assert user.phone_number is None or user.phone_number == ""


# ============================================================================
# INTEGRATION TESTS: User Authentication
# ============================================================================


class TestUserAuthentication:
    """Integration tests for user login and authentication."""

    def test_customer_login(self, customer_user):
        """
        Test: Customer can log in with correct credentials.
        """
        from django.contrib.auth import authenticate

        user = authenticate(username="testcustomer", password="testpass123")

        assert user is not None
        assert user.is_customer == True

    def test_producer_login(self, producer_user):
        """
        Test: Producer can log in with correct credentials.
        """
        from django.contrib.auth import authenticate

        user = authenticate(username="testproducer", password="testpass123")

        assert user is not None
        assert user.is_producer == True

    def test_incorrect_password_fails(self, customer_user):
        """
        Test: Login fails with incorrect password.
        """
        from django.contrib.auth import authenticate

        user = authenticate(username="testcustomer", password="wrongpassword")

        assert user is None

    def test_nonexistent_user_fails(self):
        """
        Test: Login fails for non-existent user.
        """
        from django.contrib.auth import authenticate

        user = authenticate(username="nonexistent", password="pass123")

        assert user is None


# ============================================================================
# INTEGRATION TESTS: API Endpoints
# ============================================================================


class TestAuthenticationAPI:
    """Integration tests for authentication API endpoints."""

    def test_registration_endpoint_customer(self):
        """
        Test: POST /accounts/api/v1/register/ creates customer account.
        """
        client = APIClient()

        response = client.post(
            "/accounts/api/v1/register/",
            {
                "username": "newcustomer",
                "email": "newcustomer@example.com",
                "password": "newpass123",
                "is_customer": True,
                "is_producer": False,
            },
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Verify user was created
        user = User.objects.get(username="newcustomer")
        assert user.is_customer == True

    def test_registration_endpoint_producer(self):
        """
        Test: POST /accounts/api/v1/register/ creates producer account.
        """
        client = APIClient()

        response = client.post(
            "/accounts/api/v1/register/",
            {
                "username": "newfarm",
                "email": "newfarm@example.com",
                "password": "farmpass123",
                "is_customer": False,
                "is_producer": True,
            },
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_login_endpoint(self, customer_user):
        """
        Test: POST /accounts/api/v1/login/ authenticates user.
        """
        client = APIClient()

        response = client.post(
            "/accounts/api/v1/login/",
            {
                "username": "testcustomer",
                "password": "testpass123",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_logout_endpoint(self, customer_user):
        """
        Test: POST /accounts/api/v1/logout/ logs user out.
        """
        client = APIClient()
        client.force_authenticate(user=customer_user)

        response = client.post("/accounts/api/v1/logout/")

        assert response.status_code == status.HTTP_200_OK

    def test_profile_endpoint_authenticated(self, customer_user):
        """
        Test: GET /accounts/api/v1/profile/ returns user profile.
        """
        client = APIClient()
        client.force_authenticate(user=customer_user)

        response = client.get("/accounts/api/v1/profile/")

        assert response.status_code == status.HTTP_200_OK

    def test_profile_endpoint_unauthenticated(self):
        """
        Test: Unauthenticated user cannot access profile endpoint.
        """
        client = APIClient()

        response = client.get("/accounts/api/v1/profile/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# UNIT TESTS: User Permissions
# ============================================================================


class TestUserPermissions:
    """Tests for role-based access control."""

    def test_customer_cannot_create_product(self, customer_user):
        """
        Test: Only producers can create products.
        """
        assert customer_user.is_producer == False

    def test_producer_can_create_product(self, producer_user):
        """
        Test: Producers have is_producer=True.
        """
        assert producer_user.is_producer == True

    def test_customer_can_purchase(self, customer_user):
        """
        Test: Customers can make purchases.
        """
        assert customer_user.is_customer == True


if __name__ == "__main__":
    pytest.main([__file__])
